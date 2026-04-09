from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.circuit_light.const import DATA_KEY, DOMAIN


async def test_coordinator_updates_on_state_change(hass: HomeAssistant, setup_integration) -> None:
    entry_id = setup_integration.entry_id
    entry_data = hass.data[DATA_KEY][entry_id]
    coordinator = entry_data.coordinator

    assert coordinator.data is not None
    assert coordinator.data.power_entity_id == "switch.relay"

    # Change a bulb state and ensure coordinator snapshot updates.
    hass.states.async_set("light.bulb_1", "on", {"brightness": 10})
    await hass.async_block_till_done()

    assert coordinator.data is not None
    bulb = next(b for b in coordinator.data.bulbs if b.entity_id == "light.bulb_1")
    assert bulb.attributes["brightness"] == 10

