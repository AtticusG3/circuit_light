"""Windows-only shim for the POSIX `fcntl` module.

Home Assistant's test tooling imports `homeassistant.runner`, which imports `fcntl`
unconditionally. The real `fcntl` module does not exist on Windows. This shim
exists solely to allow the Home Assistant pytest plugin to import on Windows so
we can run unit tests for this repository.

On non-Windows platforms, Python's built-in `fcntl` module will be imported
instead of this file, so this has no effect.
"""

from __future__ import annotations

import errno
from typing import Any

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def _not_supported(*_args: Any, **_kwargs: Any) -> None:
    raise OSError(errno.ENOSYS, "fcntl is not supported on this platform")


fcntl = _not_supported
ioctl = _not_supported
flock = _not_supported
lockf = _not_supported

