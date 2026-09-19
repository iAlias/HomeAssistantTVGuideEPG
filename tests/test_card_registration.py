"""Guards the card being shipped and auto-registered.

The card used to live in a root ``www/`` folder that HACS does not install, so
the only way to see it was to copy it by hand into ``config/www`` and add a
Lovelace resource — which is exactly why it appeared to be missing from
"Add card" right after configuring the integration. It now lives inside the
integration, and the integration serves and registers it on setup.

These checks do not need Home Assistant: they read the manifest, the frontend
file and ``__init__.py`` as text.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "tv_guide_epg"
CARD = COMPONENT / "frontend" / "tv-guide-epg-card.js"


def test_the_integration_depends_on_frontend_and_http():
    """Serving the card needs both components loaded first."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text("utf-8"))
    assert "frontend" in manifest["dependencies"]
    assert "http" in manifest["dependencies"]


def test_the_card_ships_inside_the_integration_folder():
    """HACS installs custom_components/<domain>, not a root-level www/."""
    assert CARD.is_file(), f"card not found at {CARD}"


def test_setup_serves_the_card_and_loads_it_on_every_dashboard():
    """A static path plus an extra module URL: no manual resource."""
    source = (COMPONENT / "__init__.py").read_text("utf-8")
    assert "async_setup" in source
    assert "async_register_static_paths" in source
    assert "add_extra_js_url" in source
    # The constant used for the served URL must match the shipped filename.
    assert CARD.name in source


def test_the_card_registers_itself_in_the_picker():
    source = CARD.read_text("utf-8")
    assert 'customElements.define("tv-guide-epg-card"' in source
    assert "customCards.push" in source
