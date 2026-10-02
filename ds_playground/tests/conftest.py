import pytest

pytest_plugins = ["pytester"]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run on any skipped or xfailed test: a skip looks like a pass (AGENTS.md §6)."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    hidden = [kind for kind in ("skipped", "xfailed", "xpassed") if reporter.stats.get(kind)]
    if hidden and exitstatus == 0:
        reporter.write_line(
            f"FAILED: tests were {', '.join(hidden)}; skips are not allowed", red=True
        )
        session.exitstatus = 1
