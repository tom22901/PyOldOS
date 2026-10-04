"""Shared pytest fixtures for PyOldOS.

Pygame needs a headless video driver (dummy) so the module-level pygame.init()
and font creation in main.py run without a display.
"""

import os
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import pygame  # noqa: E402

import main  # noqa: E402


@pytest.fixture
def wm():
    return main.WindowManager()


class FakeEvent:
    """Minimal stand-in for pygame events used by widget handlers."""

    def __init__(self, etype, **attrs):
        self.type = etype
        self.__dict__.update(attrs)


@pytest.fixture
def click():
    """Factory for MOUSEBUTTONDOWN/UP events."""

    def make(button=1, pos=(0, 0), etype=pygame.MOUSEBUTTONDOWN):
        return FakeEvent(etype, button=button, pos=pos)

    return make


@pytest.fixture
def key():
    """Factory for KEYDOWN events."""

    def make(key_code, unicode="", mod=0):
        return FakeEvent(pygame.KEYDOWN, key=key_code, unicode=unicode, mod=mod)

    return make