from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.circuit_light.const import (
    CONF_BULB_ENTITIES,
    CONF_NAME,
    CONF_POWER_ENTITY,
    DOMAIN,
)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Circuit Light",
        data={
            CONF_NAME: "Circuit Light",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1", "light.bulb_2"],
        },
    )


@pytest.fixture
async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> MockConfigEntry:
    hass.states.async_set("switch.relay", "on")
    hass.states.async_set("light.bulb_1", "on", {"brightness": 100})
    hass.states.async_set("light.bulb_2", "on", {"brightness": 200})

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry

