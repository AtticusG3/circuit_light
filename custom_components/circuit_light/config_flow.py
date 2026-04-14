from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import DOMAIN
from .const import CONF_BULB_ENTITIES, CONF_HIDE_CHILD_ENTITIES, CONF_NAME, CONF_POWER_ENTITY
from .api import ApiValidationError, async_validate_config

class CircuitLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Circuit Light."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated = await async_validate_config(
                    self.hass,
                    name=user_input[CONF_NAME],
                    power_entity_id=user_input[CONF_POWER_ENTITY],
                    bulb_entity_ids=list(user_input[CONF_BULB_ENTITIES]),
                )
            except ApiValidationError as exc:
                errors["base"] = str(exc)
            else:
                await self.async_set_unique_id(validated.power_entity_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=validated.name,
                    data={
                        CONF_NAME: validated.name,
                        CONF_POWER_ENTITY: validated.power_entity_id,
                        CONF_BULB_ENTITIES: list(validated.bulb_entity_ids),
                    },
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "light"]
                    )
                ),
                vol.Required(CONF_BULB_ENTITIES): selector.EntitySelector(
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
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()

    async def async_step_reauth(self, _entry_data: dict[str, Any]) -> config_entries.FlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated = await async_validate_config(
                    self.hass,
                    name=self._reauth_entry.title,
                    power_entity_id=user_input[CONF_POWER_ENTITY],
                    bulb_entity_ids=list(user_input[CONF_BULB_ENTITIES]),
                )
            except ApiValidationError as exc:
                errors["base"] = str(exc)
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={
                        **self._reauth_entry.data,
                        CONF_POWER_ENTITY: validated.power_entity_id,
                        CONF_BULB_ENTITIES: list(validated.bulb_entity_ids),
                    },
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_POWER_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "light"])
                ),
                vol.Required(CONF_BULB_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["light"], multiple=True)
                ),
            }
        )
        return self.async_show_form(step_id="reauth_confirm", data_schema=data_schema, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Circuit Light."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Apply changes to the config entry and reload so the entity picks up new targets.
            # Note: options flows normally only write options, but this integration's core
            # configuration lives in entry.data (power_entity / bulb_entities).
            try:
                validated = await async_validate_config(
                    self.hass,
                    name=user_input[CONF_NAME],
                    power_entity_id=user_input[CONF_POWER_ENTITY],
                    bulb_entity_ids=list(user_input[CONF_BULB_ENTITIES]),
                )
            except ApiValidationError as exc:
                errors["base"] = str(exc)
            else:
                new_options = {
                    **self.config_entry.options,
                    CONF_HIDE_CHILD_ENTITIES: bool(
                        user_input.get(CONF_HIDE_CHILD_ENTITIES, True)
                    ),
                }
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=validated.name,
                    data={
                        **self.config_entry.data,
                        CONF_NAME: validated.name,
                        CONF_POWER_ENTITY: validated.power_entity_id,
                        CONF_BULB_ENTITIES: list(validated.bulb_entity_ids),
                    },
                    options=self.config_entry.options,
                )
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data=new_options)

        # Get current values from config entry
        current_name = self.config_entry.data.get(CONF_NAME, "")
        current_power_entity = self.config_entry.data.get(CONF_POWER_ENTITY, "")
        current_bulb_entities = self.config_entry.data.get(CONF_BULB_ENTITIES, [])
        current_hide_children = self.config_entry.options.get(CONF_HIDE_CHILD_ENTITIES, True)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=current_name): str,
                vol.Required(CONF_POWER_ENTITY, default=current_power_entity): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["switch", "light"]
                    )
                ),
                vol.Required(CONF_BULB_ENTITIES, default=current_bulb_entities): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["light"], multiple=True
                    )
                ),
                vol.Required(
                    CONF_HIDE_CHILD_ENTITIES,
                    default=bool(current_hide_children),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)