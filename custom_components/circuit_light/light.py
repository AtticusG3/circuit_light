from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_NAME,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ATTR_XY_COLOR,
    ColorMode,
    EFFECT_OFF,
    LightEntity,
    LightEntityFeature,
    filter_turn_on_params,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify

from .const import (
    ATTR_COLOR_TEMP_KELVIN,
    CONF_NAME,
    DATA_KEY,
    DOMAIN,
)
from .effects import EFFECT_LIST
from .coordinator import (
    CircuitLightCoordinator,
    snapshot_available,
    snapshot_brightness,
    snapshot_color_mode,
    snapshot_color_temp_kelvin,
    snapshot_max_color_temp_kelvin,
    snapshot_min_color_temp_kelvin,
    snapshot_hs_color,
    snapshot_is_on,
    snapshot_rgb_color,
    snapshot_supported_color_modes,
    snapshot_supported_features,
    snapshot_xy_color,
)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Circuit Light platform."""
    entry_data = hass.data[DATA_KEY][entry.entry_id]
    async_add_entities([CircuitLight(entry, entry_data.coordinator)])


class CircuitLight(CoordinatorEntity[CircuitLightCoordinator], LightEntity):
    """Representation of a Circuit Light."""

    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, coordinator: CircuitLightCoordinator) -> None:
        """Initialize the Circuit Light."""
        self.entry = entry
        super().__init__(coordinator)
        # Use the config entry unique_id (power entity id) for stable entity registry entries.
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_suggested_object_id = slugify(self.name or entry.title or entry.entry_id)
        self._attr_effect = None
        self._effect_task: asyncio.Task[None] | None = None

    async def _async_cancel_effect_task(self) -> None:
        """Cancel an in-flight effect and wait for it to stop."""
        task = self._effect_task
        if task is None:
            return
        self._effect_task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        if self._attr_effect is not None:
            self._attr_effect = None
            self.async_write_ha_state()

    @property
    def power_entity_id(self) -> str:
        """Return the power entity ID."""
        return self.coordinator.power_entity_id

    @property
    def bulb_entities(self) -> list[str]:
        """Return the bulb entity IDs."""
        return list(self.coordinator.bulb_entity_ids)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        await self._async_cancel_effect_task()

    @property
    def name(self) -> str | None:
        return self.entry.data.get(CONF_NAME) or self.entry.title

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return snapshot_is_on(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return true if device is available."""
        return snapshot_available(self.coordinator.data)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        return snapshot_brightness(self.coordinator.data)

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in kelvin."""
        return snapshot_color_temp_kelvin(self.coordinator.data)

    @property
    def min_color_temp_kelvin(self) -> int | None:
        return snapshot_min_color_temp_kelvin(self.coordinator.data)

    @property
    def max_color_temp_kelvin(self) -> int | None:
        return snapshot_max_color_temp_kelvin(self.coordinator.data)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the HS color value."""
        return snapshot_hs_color(self.coordinator.data)

    @property
    def xy_color(self) -> tuple[float, float] | None:
        return snapshot_xy_color(self.coordinator.data)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return snapshot_rgb_color(self.coordinator.data)

    @property
    def color_mode(self) -> ColorMode | str:
        """Return the color mode of the light."""
        if self._attr_effect is not None:
            # While rendering an effect, Home Assistant expects a restrictive color_mode.
            # These effects do not support adjustments, so report on/off.
            return ColorMode.ONOFF
        return snapshot_color_mode(self.coordinator.data)

    @property
    def supported_color_modes(self) -> set[ColorMode | str]:
        """Flag supported color modes."""
        return snapshot_supported_color_modes(self.coordinator.data)

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return snapshot_supported_features(self.coordinator.data)

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return list(EFFECT_LIST)

    @property
    def effect(self) -> str:
        """Return the current effect."""
        return self._attr_effect or EFFECT_OFF

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.entry.title,
            manufacturer="Circuit Light",
            model="Virtual Circuit Light",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Always request power on; coordinator/state updates will reflect availability.
        power_domain = self.power_entity_id.split(".", 1)[0]
        await self.hass.services.async_call(power_domain, "turn_on", {"entity_id": self.power_entity_id}, blocking=False)

        # Handle effect
        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] is not None:
            effect_name = kwargs[ATTR_EFFECT]
            if effect_name == EFFECT_OFF:
                await self._async_cancel_effect_task()
                return

            # Stop any previous effect before starting a new one.
            await self._async_cancel_effect_task()
            self._attr_effect = effect_name
            self._effect_task = self.hass.async_create_background_task(
                self._run_effect(effect_name),
                name=f"{DOMAIN} effect: {effect_name}",
            )
            self.async_write_ha_state()
            return

        # Handle color/brightness/transition
        if any(
            key in kwargs
            for key in (
                ATTR_BRIGHTNESS,
                ATTR_COLOR_NAME,
                ATTR_COLOR_TEMP_KELVIN,
                ATTR_HS_COLOR,
                ATTR_RGB_COLOR,
                ATTR_TRANSITION,
                ATTR_XY_COLOR,
            )
        ):
            await self._async_cancel_effect_task()
            # Turn on bulbs with provided kwargs, normalized to HA's current service schema.
            service_data = filter_turn_on_params(self, kwargs)
            await self.hass.services.async_call(
                "light",
                "turn_on",
                {**service_data, "entity_id": self.bulb_entities},
                blocking=False,
            )
            self.async_write_ha_state()
            return

        # Bare turn on (no kwargs)
        await self._async_cancel_effect_task()
        # Turn on bulbs. Avoid persisting behavior here; underlying lights keep their own last state.
        await self.hass.services.async_call(
            "light",
            "turn_on",
            {"entity_id": self.bulb_entities},
            blocking=False,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Cancel any active effect
        await self._async_cancel_effect_task()

        # Turn off power entity only
        await self.hass.services.async_call(
            self.power_entity_id.split(".", 1)[0],
            "turn_off",
            {"entity_id": self.power_entity_id},
            blocking=False,
        )
        self.async_write_ha_state()

    async def _run_effect(self, effect_name: str) -> None:
        """Run an effect."""
        from .effects import async_run_effect

        try:
            await async_run_effect(
                self.hass,
                effect_name=effect_name,
                bulb_entity_ids=tuple(self.bulb_entities),
            )
        except asyncio.CancelledError:
            pass