from __future__ import annotations

import asyncio
import time
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_COLOR_TEMP_MIREDS,
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
    snapshot_color_temp,
    snapshot_hs_color,
    snapshot_is_on,
    snapshot_supported_color_modes,
    snapshot_supported_features,
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

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry, coordinator: CircuitLightCoordinator) -> None:
        """Initialize the Circuit Light."""
        self.entry = entry
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}"
        self._attr_effect = None
        self._effect_task: asyncio.Task[None] | None = None

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
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass

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
    def color_temp(self) -> float | None:
        """Return the color temperature in mireds."""
        return snapshot_color_temp(self.coordinator.data)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the HS color value."""
        return snapshot_hs_color(self.coordinator.data)

    @property
    def color_mode(self) -> ColorMode | str:
        """Return the color mode of the light."""
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
        return EFFECT_LIST

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self._attr_effect

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
        # Turn on power entity if it's off
        if not self.is_on:
            await self.hass.services.async_call(
                "homeassistant", "turn_on", {"entity_id": self.power_entity_id}, blocking=False
            )
            # Wait for power entity to turn on (timeout 5s)
            wait_start = time.time()
            while time.time() - wait_start < 5:
                if snapshot_is_on(self.coordinator.data):
                    break
                await asyncio.sleep(0.1)
            # Note: Timeout handling is implicit - we just continue after 5 seconds

        # Wait for at least one bulb to become available (timeout 5s)
        wait_start = time.time()
        while time.time() - wait_start < 5:
            available_bulbs = [
                entity_id
                for entity_id in self.bulb_entities
                if self.hass.states.get(entity_id)
                and self.hass.states.get(entity_id).state != STATE_UNAVAILABLE
            ]
            if available_bulbs:
                break
            await asyncio.sleep(0.1)
        # Note: Timeout handling is implicit - we just continue after 5 seconds

        # Handle effect
        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] is not None:
            effect_name = kwargs[ATTR_EFFECT]
            if self._effect_task:
                self._effect_task.cancel()
                try:
                    await self._effect_task
                except asyncio.CancelledError:
                    pass
            self._attr_effect = effect_name
            self._effect_task = self.entry.async_create_background_task(
                self._run_effect(effect_name)
            )
            self.async_write_ha_state()
            return

        # Handle color/brightness/transition
        if any(
            key in kwargs
            for key in (
                ATTR_BRIGHTNESS,
                ATTR_COLOR_TEMP_MIREDS,
                ATTR_COLOR_TEMP_KELVIN,
                ATTR_HS_COLOR,
                ATTR_TRANSITION,
            )
        ):
            if self._effect_task:
                self._effect_task.cancel()
                try:
                    await self._effect_task
                except asyncio.CancelledError:
                    pass
            self._attr_effect = None
            # Turn on bulbs with provided kwargs
            await self.hass.services.async_call(
                "light", "turn_on", {**kwargs, "entity_id": self.bulb_entities}, blocking=False
            )
            self.async_write_ha_state()
            return

        # Bare turn on (no kwargs)
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass
        self._attr_effect = None
        # Turn on bulbs with last known brightness (default 255)
        last_brightness = self.entry.options.get(ATTR_BRIGHTNESS)
        if last_brightness is None:
            last_brightness = 255
        await self.hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_BRIGHTNESS: last_brightness, "entity_id": self.bulb_entities},
            blocking=False,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Cancel any active effect
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass
        self._attr_effect = None

        # Turn off power entity only
        await self.hass.services.async_call(
            "homeassistant", "turn_off", {"entity_id": self.power_entity_id}, blocking=False
        )
        self.async_write_ha_state()

    async def _run_effect(self, effect_name: str) -> None:
        """Run an effect."""
        from .effects import (
            effect_christmas_lights,
            effect_colour_cycle,
            effect_rainbow_chase,
            effect_colour_wipe,
            effect_strobe,
            effect_candle_flicker,
            effect_police,
            effect_warm_fade,
        )

        effect_map = {
            "Christmas Lights": effect_christmas_lights,
            "Colour Cycle": effect_colour_cycle,
            "Rainbow Chase": effect_rainbow_chase,
            "Colour Wipe": effect_colour_wipe,
            "Strobe": effect_strobe,
            "Candle Flicker": effect_candle_flicker,
            "Police": effect_police,
            "Warm Fade": effect_warm_fade,
        }

        effect_func = effect_map.get(effect_name)
        if effect_func:
            try:
                await effect_func(self)
            except asyncio.CancelledError:
                pass