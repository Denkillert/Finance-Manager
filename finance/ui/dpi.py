"""Корректная работа с масштабированием экрана в Windows."""

from __future__ import annotations

import ctypes
import sys


def enable_dpi_awareness() -> None:
    """Сообщает Windows, что приложение само учитывает DPI.

    Без этого при масштабировании 125–150 % система растягивает окно,
    и часть интерфейса уезжает за границы экрана.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except (AttributeError, OSError):
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
