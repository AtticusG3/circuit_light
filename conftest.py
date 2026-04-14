"""Pytest configuration for running HA-style tests on Windows.

The upstream `pytest-homeassistant-custom-component` plugin disables socket creation
in `pytest_runtest_setup`. That is compatible with Linux/macOS where asyncio can
create its self-pipe without TCP sockets, but it breaks on Windows where
`asyncio.ProactorEventLoop` uses a TCP socketpair fallback during loop creation.

We keep the rest of the HA test harness intact, but skip socket disabling on Windows
so the event loop can be created.
"""

from __future__ import annotations

import sys
from typing import Any


def pytest_configure(config: Any) -> None:
    if not sys.platform.startswith("win"):
        return

    import pytest_socket  # noqa: PLC0415

    # The HA pytest plugin disables sockets in its `pytest_runtest_setup` hook.
    # On Windows, the default asyncio event loop needs TCP sockets for its internal
    # self-pipe (socketpair fallback). Make disable_socket a no-op.
    def _disable_socket_noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    pytest_socket.disable_socket = _disable_socket_noop  # type: ignore[assignment]

