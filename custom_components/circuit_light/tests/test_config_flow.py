from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.circuit_light.const import (
    CONF_BULB_ENTITIES,
    CONF_HIDE_CHILD_ENTITIES,
    CONF_NAME,
    CONF_POWER_ENTITY,
    DOMAIN,
)


async def test_config_flow_success(hass: HomeAssistant) -> None:
    hass.states.async_set("switch.relay", "off")
    hass.states.async_set("light.bulb_1", "on")
    hass.states.async_set("light.bulb_2", "on")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Circuit",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1", "light.bulb_2"],
        },
    )
    assert result2["type"] == "create_entry"
    assert result2["title"] == "My Circuit"


async def test_config_flow_invalid_power_entity(hass: HomeAssistant) -> None:
    hass.states.async_set("light.bulb_1", "on")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Circuit",
            CONF_POWER_ENTITY: "switch.missing",
            CONF_BULB_ENTITIES: ["light.bulb_1"],
        },
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "invalid_power_entity"


async def test_config_flow_invalid_bulb_entity(hass: HomeAssistant) -> None:
    hass.states.async_set("switch.relay", "off")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Circuit",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.missing"],
        },
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "invalid_bulb_entities"


async def test_options_flow_updates_entry(hass: HomeAssistant, setup_integration) -> None:
    entry = setup_integration

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Updated Circuit",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1"],
            CONF_HIDE_CHILD_ENTITIES: False,
        },
    )
    assert result2["type"] == "create_entry"
    await hass.async_block_till_done()

    updated = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated is not None
    assert updated.data[CONF_NAME] == "Updated Circuit"
    assert updated.data[CONF_BULB_ENTITIES] == ["light.bulb_1"]
    assert updated.options[CONF_HIDE_CHILD_ENTITIES] is False


async def test_reauth_flow_success(hass: HomeAssistant, setup_integration) -> None:
    entry = setup_integration

    # Start reauth flow for the existing entry.
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data={},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1", "light.bulb_2"],
        },
    )
    assert result2["type"] == "abort"
    assert result2["reason"] == "reauth_successful"


@pytest.mark.parametrize(
    ("power_entity", "bulb_entities", "expected_error"),
    [
        ("switch.missing", ["light.bulb_1"], "invalid_power_entity"),
        ("switch.relay", ["light.missing"], "invalid_bulb_entities"),
    ],
)
async def test_reauth_flow_invalid_entities(
    hass: HomeAssistant,
    setup_integration,
    power_entity: str,
    bulb_entities: list[str],
    expected_error: str,
) -> None:
    entry = setup_integration

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data={},
    )
    assert result["type"] == "form"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_POWER_ENTITY: power_entity,
            CONF_BULB_ENTITIES: bulb_entities,
        },
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == expected_error
