"""An OpenAI-compatible endpoint behind the gateway port: the skill's binding 2, opt-in by D4.

Never a fallback. The key comes from the OS secret store under the account the binding names; the
project's data policy and the owner's spend limit are part of the binding and are recorded with the
readiness event, so they are shown before the first use; a charge the limit cannot cover is refused
before the request is sent. Tested against llama-server itself, an OpenAI-compatible server on this
machine: no key of the owner's, no spend, nothing leaves the machine (D4 = B).
"""

import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

from dsp.adapters.llama_server import assemble, typed_probe
from dsp.contracts.errors import DspError, ErrorCode
from dsp.ports import SecretStore

STORE = (  # how the owner stores a key; the secret port reads exactly these names (D4)
    "`security add-generic-password -s dev.dsp.assistant -a {account} -w` (macOS) or "
    "`secret-tool store --label=dsp service dev.dsp.assistant account {account}` (Linux)"
)


class OpenAICompatible:
    """One remote binding's endpoint: keyed, probed, bounded by its limits and its spend."""

    def __init__(self, binding: Mapping[str, Any], *, secrets: SecretStore) -> None:
        self.binding, self.secrets = dict(binding), secrets
        self.account = binding["endpoint"]["api_key_ref"].removeprefix("secret://local/")
        base = binding["endpoint"]["base_url"].removesuffix("/v1").rstrip("/")
        if base.startswith("unix://"):  # a local server on a socket (llama-server on Linux)
            transport = httpx.HTTPTransport(uds=base.removeprefix("unix://"))
            self.client = httpx.Client(base_url="http://remote", transport=transport, timeout=30)
        else:
            self.client = httpx.Client(base_url=base, timeout=30)
        self.key, self.ready, self.spent_minor = "", False, 0
        self.failure: str | None = None

    def headers(self) -> dict[str, str]:
        """The key, held in this process's memory only while the binding is ready."""
        return {"Authorization": f"Bearer {self.key}"}

    def start(self, proceed: Callable[[], bool] = lambda: True) -> dict[str, Any]:
        """Check the policy, fetch the key, see the model served and pass the typed probe."""
        if self.binding["data_policy"]["allowed"] == "none":
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                "the project's data policy lets nothing leave the machine",
            )
        key = self.secrets.get(self.account)
        if not key:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"no key stored for account {self.account}: " + STORE.format(account=self.account),
            )
        self.key, self.failure, started = key, None, time.monotonic()
        try:
            served = self.client.get("/v1/models", headers=self.headers())
        except httpx.HTTPError as error:
            self.stop()
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"the endpoint did not answer ({type(error).__name__})",
            ) from None
        if served.status_code != 200:
            self.stop()
            refused = served.status_code in (401, 403)
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"the endpoint refused the key for account {self.account}"
                if refused
                else f"the endpoint answered {served.status_code}",
            )
        model = self.binding["provider"]["model"]
        ids = [str(m.get("id")) for m in served.json().get("data", [])]
        if model not in ids:
            self.stop()
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"model {model} is not served (served: {', '.join(ids)[:200]})",
            )
        self.ready = True
        try:
            typed_probe(self, self.binding["limits"]["generation_deadline_seconds"])
        except DspError:
            self.stop()
            raise
        observed = {"model": model, "probe_seconds": round(time.monotonic() - started, 3)}
        return observed | {"placement": self.binding["placement"]}

    def alive(self) -> bool:
        """Ready and no call has failed since."""
        return self.ready and self.failure is None

    def stop(self) -> None:
        """Forget the key; nothing runs here."""
        self.ready, self.key = False, ""

    def charge(self, tokens: int) -> int:
        """The charge for tokens at the binding's price, in minor units, rounded up."""
        price = int(self.binding["spend"]["price_per_million_tokens_minor"])
        return -(-tokens * price // 1_000_000)

    def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        deadline: float,
        seed: int,
        temperature: float,
        stop: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        """One streamed chat completion within the deadline and within the owner's spend limit."""
        if not self.alive():
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE, self.failure or "the endpoint is not ready"
            )
        limit = self.binding["limits"]["max_external_charge_minor"]
        projected = self.charge(self.count(json.dumps(list(messages))) + max_tokens)
        if self.spent_minor + projected > limit:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"the spend limit of GBP {limit / 100:.2f} would be exceeded: GBP "
                f"{self.spent_minor / 100:.2f} spent, up to GBP {projected / 100:.2f} for this",
            )
        body: dict[str, Any] = {
            "model": self.binding["provider"]["model"],
            "messages": list(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
            "top_p": self.binding["decoding"]["top_p"],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            body["tools"] = list(tools)
        try:
            with self.client.stream(
                "POST", "/v1/chat/completions", json=body, headers=self.headers(), timeout=deadline
            ) as answer:
                if answer.status_code != 200:
                    self.failure = f"the endpoint answered {answer.status_code}"
                    raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure)
                found = assemble(answer.iter_lines(), stop)
        except httpx.TimeoutException:
            self.failure = f"no answer within the {deadline:g} s generation deadline"
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure) from None
        except httpx.HTTPError as error:
            self.failure = f"the endpoint did not answer ({type(error).__name__})"
            raise DspError(ErrorCode.ASSISTANT_UNAVAILABLE, self.failure) from None
        self.spent_minor += self.charge(int(found["usage"].get("total_tokens") or 0))
        return found

    def count(self, text: str) -> int:
        """The endpoint's own count when it tokenizes (llama-server, vLLM), else a bound.

        One token per two bytes is deliberately high: an input the endpoint would cut is refused
        here instead, by the D17 input limit.
        """
        try:
            answer = self.client.post("/tokenize", json={"content": text}, headers=self.headers())
        except httpx.HTTPError as error:
            raise DspError(
                ErrorCode.ASSISTANT_UNAVAILABLE,
                f"the endpoint did not answer ({type(error).__name__})",
            ) from None
        if answer.status_code == 200:
            return len(answer.json()["tokens"])
        if answer.status_code == 404:
            return len(text.encode()) // 2 + 1
        raise DspError(
            ErrorCode.ASSISTANT_UNAVAILABLE, f"the tokenizer answered {answer.status_code}"
        )
