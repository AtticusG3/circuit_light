from __future__ import annotations

import sys


def test_pytest_conftest_windows_hooks_are_callable(monkeypatch) -> None:
    # Cover test conftest's Windows-only socket enabling hooks.
    from custom_components.circuit_light.tests import conftest as test_conftest

    monkeypatch.setattr(sys, "platform", "win32")
    test_conftest.pytest_sessionstart()
    test_conftest.pytest_runtest_setup()

