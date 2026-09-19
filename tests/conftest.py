"""Make the integration's pure-logic modules importable without a full Home
Assistant installation, using real package-relative imports.

A synthetic ``custom_components.tv_guide_epg`` package (and its ``sources``
sub-package) is registered directly in ``sys.modules``, with ``__path__``
pointing at the real component directories, so that relative imports such as
``from .base import Schedule`` resolve normally without ever executing the real
``__init__.py`` (which pulls in the rest of ``homeassistant``). Only the small
pieces of ``homeassistant`` that ``coordinator.py`` needs for typing/base-class
purposes are stubbed. Mirrors the approach used in the ``tv_guide_multi``
project's ``conftest.py``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "tv_guide_epg"
PACKAGE = "custom_components.tv_guide_epg"
SOURCES_PACKAGE = f"{PACKAGE}.sources"


class _GenericStub:
    """Base class that tolerates ``Stub[SomeType]`` subscription syntax."""

    def __class_getitem__(cls, item):
        return cls


def _install_stub_homeassistant() -> None:
    if "homeassistant" in sys.modules:
        return

    modules = {name: types.ModuleType(name) for name in (
        "homeassistant",
        "homeassistant.core",
        "homeassistant.helpers",
        "homeassistant.helpers.update_coordinator",
    )}

    class HomeAssistant:
        pass

    class DataUpdateCoordinator(_GenericStub):
        def __init__(self, hass, logger, *, name=None, update_interval=None):
            self.data = None
            self.update_interval = update_interval

        async def async_refresh(self):
            self.data = await self._async_update_data()

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

    modules["homeassistant.core"].HomeAssistant = HomeAssistant
    modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = DataUpdateCoordinator

    sys.modules.update(modules)


def _register_component_package() -> None:
    if SOURCES_PACKAGE in sys.modules:
        return

    root = types.ModuleType("custom_components")
    root.__path__ = []
    sys.modules.setdefault("custom_components", root)

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(COMPONENT_DIR)]
    sys.modules[PACKAGE] = package

    sources_package = types.ModuleType(SOURCES_PACKAGE)
    sources_package.__path__ = [str(COMPONENT_DIR / "sources")]
    sys.modules[SOURCES_PACKAGE] = sources_package


_install_stub_homeassistant()
_register_component_package()
