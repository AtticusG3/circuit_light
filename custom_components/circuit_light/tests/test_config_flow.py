from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.circuit_light.const import CONF_BULB_ENTITIES, CONF_NAME, CONF_POWER_ENTITY, DOMAIN


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

