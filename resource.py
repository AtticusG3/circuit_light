"""Windows-only shim for the POSIX `resource` module.

Home Assistant imports `homeassistant.util.resource`, which imports the stdlib
`resource` module unconditionally. That module is not available on Windows.

This shim exists to allow importing Home Assistant in unit tests on Windows.
If any code path actually requires real resource limits, it will raise.
"""

from __future__ import annotations

import errno
from typing import Any

RLIM_INFINITY = -1
RLIMIT_NOFILE = 7


def _not_supported(*_args: Any, **_kwargs: Any) -> None:
    raise OSError(errno.ENOSYS, "resource limits are not supported on this platform")


def getrlimit(_resource: int) -> tuple[int, int]:
    # Return a harmless default that won't be used for enforcement in tests.
    return (RLIM_INFINITY, RLIM_INFINITY)


def setrlimit(_resource: int, _limits: tuple[int, int]) -> None:
    _not_supported()


getrusage = _not_supported

