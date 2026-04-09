from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector
from homeassistant.helpers.entity import async_get_entity_id

from .const import DOMAIN
from .strings import (
    NAME,
    POWER_ENTITY,
    BULB_ENTITIES,
    CONFIG_FLOW_TITLE,
    CONFIG_FLOW_DESCRIPTION,
    BULB_ORDER_NOTE,
    OPTIONS_FLOW_TITLE,
    OPTIONS_FLOW_DESCRIPTION,
)

class CircuitLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Circuit Light."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Validate entities exist
            hass = self.hass
            power_entity_id = user_input[POWER_ENTITY]
            bulb_entity_ids = user_input[BULB_ENTITIES]

            # Check if power entity exists
            power_entity = await async_get_entity_id(
                hass, "switch", power_entity_id.split(".")[-1]
            ) or await async_get_entity_id(
                hass, "light", power_entity_id.split(".")[-1]
            )
            if not power_entity:
                errors["base"] = "invalid_power_entity"

            # Check if bulb entities exist
            for bulb_id in bulb_entity_ids:
                bulb_entity = await async_get_entity_id(
                    hass, "light", bulb_id.split(".")[-1]
                )
                if not bulb_entity:
                    errors["base"] = "invalid_bulb_entities"
                    break

            if not errors:
                return self.async_create_entry(
                    title=user_input[NAME],
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(NAME): str,
                vol.Required(POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "light"]
                    )
                ),
                vol.Required(BULB_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light"], multiple=True
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "bulb_order_note": BULB_ORDER_NOTE
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Circuit Light."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry with new data
            return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        current_name = self.config_entry.data.get(NAME, "")
        current_power_entity = self.config_entry.data.get(POWER_ENTITY, "")
        current_bulb_entities = self.config_entry.data.get(BULB_ENTITIES, [])

        data_schema = vol.Schema(
            {
                vol.Required(NAME, default=current_name): str,
                vol.Required(POWER_ENTITY, default=current_power_entity): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "light"]
                    )
                ),
                vol.Required(BULB_ENTITIES, default=current_bulb_entities): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light"], multiple=True
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={
                "bulb_order_note": BULB_ORDER_NOTE
            },
        )