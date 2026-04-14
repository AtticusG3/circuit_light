from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.circuit_light import async_reload_entry
from custom_components.circuit_light.const import DATA_KEY


async def test_async_reload_entry_runs_unload_and_setup(hass: HomeAssistant, setup_integration) -> None:
    entry = setup_integration
    assert entry.entry_id in hass.data[DATA_KEY]

    await async_reload_entry(hass, entry)
    await hass.async_block_till_done()

    assert entry.entry_id in hass.data[DATA_KEY]

