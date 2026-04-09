from __future__ import annotations

from homeassistant.core import HomeAssistant


async def test_light_entity_uses_coordinator_data(hass: HomeAssistant, setup_integration) -> None:
    state = hass.states.get("light.circuit_light")
    # Entity id is created by HA; for custom components, default entity_id is derived from name/title.
    # To avoid brittle assumptions about entity_id generation, locate it by unique_id.
    entity_reg = await hass.helpers.entity_registry.async_get_registry()
    reg_entry = next(
        e
        for e in entity_reg.entities.values()
        if e.config_entry_id == setup_integration.entry_id and e.domain == "light"
    )
    state = hass.states.get(reg_entry.entity_id)
    assert state is not None

    # Power is 'on' from conftest, so combined should be on.
    assert state.state == "on"

    # Brightness should be the average of 100 and 200 (rounds to 150).
    assert state.attributes.get("brightness") == 150

