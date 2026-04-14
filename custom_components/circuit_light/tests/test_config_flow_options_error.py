from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.circuit_light.const import CONF_BULB_ENTITIES, CONF_NAME, CONF_POWER_ENTITY, DOMAIN


async def test_options_flow_reports_validation_error(hass: HomeAssistant, setup_integration, monkeypatch) -> None:
    from custom_components.circuit_light import config_flow
    from custom_components.circuit_light.api import ApiValidationError

    async def _raise(*_args, **_kwargs):
        raise ApiValidationError("boom")

    monkeypatch.setattr(config_flow, "async_validate_config", _raise)

    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] == FlowResultType.FORM

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "X",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1"],
            "hide_child_entities": True,
        },
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"]["base"] == "boom"

