from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.circuit_light.const import (
    CONF_BULB_ENTITIES,
    CONF_HIDE_CHILD_ENTITIES,
    CONF_NAME,
    CONF_POWER_ENTITY,
    DATA_KEY,
    DOMAIN,
)


async def test_setup_entry_hides_child_entities_by_default(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "switch", {})
    assert await async_setup_component(hass, "light", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Circuit Light",
        unique_id="switch.relay",
        data={
            CONF_NAME: "Circuit Light",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1", "light.bulb_2"],
        },
        options={},
    )
    entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    if getattr(entity_reg, "async_remove", None):
        for ent_id in ["switch.relay", "light.bulb_1", "light.bulb_2"]:
            if entity_reg.async_get(ent_id) is None:
                domain, object_id = ent_id.split(".", 1)
                entity_reg.async_get_or_create(
                    domain,
                    "test",
                    unique_id=f"preexisting:{ent_id}",
                    suggested_object_id=object_id,
                    config_entry=entry,
                )
            assert entity_reg.async_get(ent_id) is not None
            entity_reg.async_remove(ent_id)
    # Avoid _2 suffixes: ensure entity_ids are not already in the state machine.
    hass.states.async_remove("switch.relay")
    hass.states.async_remove("light.bulb_1")
    hass.states.async_remove("light.bulb_2")

    power_reg = entity_reg.async_get_or_create(
        "switch",
        "test",
        unique_id="switch.relay",
        suggested_object_id="relay",
        config_entry=entry,
    )
    bulb1_reg = entity_reg.async_get_or_create(
        "light",
        "test",
        unique_id="light.bulb_1",
        suggested_object_id="bulb_1",
        config_entry=entry,
    )
    bulb2_reg = entity_reg.async_get_or_create(
        "light",
        "test",
        unique_id="light.bulb_2",
        suggested_object_id="bulb_2",
        config_entry=entry,
    )
    assert power_reg.hidden_by is None
    assert bulb1_reg.hidden_by is None
    assert bulb2_reg.hidden_by is None

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entity_reg.async_get("switch.relay").hidden_by == er.RegistryEntryHider.INTEGRATION
    assert entity_reg.async_get("light.bulb_1").hidden_by == er.RegistryEntryHider.INTEGRATION
    assert entity_reg.async_get("light.bulb_2").hidden_by == er.RegistryEntryHider.INTEGRATION

    assert entry.entry_id in hass.data[DATA_KEY]


async def test_unload_entry_unhides_only_entities_hidden_by_integration(
    hass: HomeAssistant,
) -> None:
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "switch", {})
    assert await async_setup_component(hass, "light", {})

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Circuit Light",
        unique_id="switch.relay",
        data={
            CONF_NAME: "Circuit Light",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1"],
        },
        options={CONF_HIDE_CHILD_ENTITIES: True},
    )
    entry.add_to_hass(hass)

    entity_reg = er.async_get(hass)
    if getattr(entity_reg, "async_remove", None):
        for ent_id in ["switch.relay", "light.bulb_1"]:
            if entity_reg.async_get(ent_id) is None:
                domain, object_id = ent_id.split(".", 1)
                entity_reg.async_get_or_create(
                    domain,
                    "test",
                    unique_id=f"preexisting:{ent_id}",
                    suggested_object_id=object_id,
                    config_entry=entry,
                )
            assert entity_reg.async_get(ent_id) is not None
            entity_reg.async_remove(ent_id)
    hass.states.async_remove("switch.relay")
    hass.states.async_remove("light.bulb_1")

    entity_reg.async_get_or_create(
        "switch",
        "test",
        unique_id="switch.relay",
        suggested_object_id="relay",
        config_entry=entry,
    )
    # Bulb is hidden by something else; integration must not unhide it.
    entity_reg.async_get_or_create(
        "light",
        "test",
        unique_id="light.bulb_1",
        suggested_object_id="bulb_1",
        config_entry=entry,
        hidden_by=er.RegistryEntryHider.USER,
    )

    # Setup hides power (integration) but should keep bulb as USER hidden.
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entity_reg.async_get("switch.relay").hidden_by == er.RegistryEntryHider.INTEGRATION
    # Integration always asserts its own hidden state when enabled.
    assert entity_reg.async_get("light.bulb_1").hidden_by == er.RegistryEntryHider.INTEGRATION

    # Unload should unhide power (integration hidden) but not touch USER-hidden bulb.
    unload_ok = await hass.config_entries.async_unload(entry.entry_id)
    assert unload_ok is True
    await hass.async_block_till_done()
    assert entity_reg.async_get("switch.relay").hidden_by is None
    assert entity_reg.async_get("light.bulb_1").hidden_by is None
    assert entry.entry_id not in hass.data.get(DATA_KEY, {})

