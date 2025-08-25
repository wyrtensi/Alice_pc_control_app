"""Subset of system actions decoupled from MIDI triggers."""

from __future__ import annotations

import platform
import webbrowser
from ctypes import POINTER, cast

import logging

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from comtypes import CLSCTX_ALL  # type: ignore
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

    PYCAW_AVAILABLE = True
except Exception:  # pragma: no cover - handled at runtime
    PYCAW_AVAILABLE = False


def open_website(url: str) -> None:
    """Open a URL in the default browser."""
    logger.debug("Opening website: %s", url)
    webbrowser.open(url)


def get_volume() -> int:
    """Return the current master volume level (0-100).

    Raises:
        NotImplementedError: If volume control is unavailable on this platform.
    """
    if platform.system() == "Windows" and PYCAW_AVAILABLE:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(volume.GetMasterVolumeLevelScalar() * 100)
    raise NotImplementedError(
        "Volume control only supported on Windows with pycaw installed"
    )


def set_volume(value: int) -> int:
    """Set the master volume level.

    Args:
        value: Desired volume percentage (0-100).

    Returns:
        The volume level that was set.

    Raises:
        ValueError: If *value* is outside 0-100.
        NotImplementedError: If volume control is unavailable.
    """
    if not 0 <= value <= 100:
        raise ValueError("Volume must be between 0 and 100")
    if platform.system() == "Windows" and PYCAW_AVAILABLE:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(value / 100, None)
        return value
    raise NotImplementedError(
        "Volume control only supported on Windows with pycaw installed"
    )
