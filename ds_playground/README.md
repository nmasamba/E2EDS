# DS Playground

A desktop data-science workspace that analyses data and trains models on demand. It is being built sprint by
sprint from [prompts.md](prompts.md) under [AGENTS.md](AGENTS.md); the specification is the planning suite in
the parent folder. Current state and what is not built yet: [STATUS.md](STATUS.md).

## What works today (Sprint 1)

Profile a CSV file and export a versioned, hash-verified pack. Every row is read; nothing is sampled. Files
over the documented bounds (50 MiB, 100,000 rows, 200 columns) are refused rather than truncated.

```bash
uv sync --frozen
```

```bash
uv run dsp profile path/to/file.csv --out path/to/existing/folder
```

```bash
uv run dsp verify path/to/existing/folder/v1
```

The pack holds `manifest.json` (relative paths and SHA-256 digests), `profile.json` and a self-contained
`report.html`. Each export goes to a new `vN` folder; earlier versions are never overwritten. Local state
(ledger and artifact store) lives in `~/.dsp`, or in `DSP_HOME` if set.

## Development

```bash
make verify
```

```bash
make verify-linux
```

`make verify` is the gate: format, lint, strict types, import boundaries and tests with coverage. `make
verify-linux` runs the same gate in a Linux container. `make test-fast` is the inner loop.
