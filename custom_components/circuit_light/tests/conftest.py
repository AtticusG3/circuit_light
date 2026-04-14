from __future__ import annotations

import sys

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.circuit_light.const import (
    CONF_BULB_ENTITIES,
    CONF_NAME,
    CONF_POWER_ENTITY,
    DOMAIN,
)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Circuit Light",
        data={
            CONF_NAME: "Circuit Light",
            CONF_POWER_ENTITY: "switch.relay",
            CONF_BULB_ENTITIES: ["light.bulb_1", "light.bulb_2"],
        },
    )


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations) -> None:
    """Enable loading custom integrations from this repo."""
    return None


@pytest.fixture
async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> MockConfigEntry:
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "switch", {})
    hass.states.async_set("switch.relay", "on")
    hass.states.async_set(
        "light.bulb_1",
        "on",
        {"brightness": 100, "supported_color_modes": ["brightness"], "color_mode": "brightness"},
    )
    hass.states.async_set(
        "light.bulb_2",
        "on",
        {"brightness": 200, "supported_color_modes": ["brightness"], "color_mode": "brightness"},
    )

    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup() -> None:
    """Ensure Windows can create the default asyncio event loop.

    The Home Assistant pytest plugin disables socket creation by default.
    On Windows, asyncio's proactor loop uses TCP sockets internally (socketpair fallback),
    which fails when sockets are disabled. Re-enable sockets for the test run.
    """
    if sys.platform.startswith("win"):
        import pytest_socket  # noqa: PLC0415

        pytest_socket.enable_socket()


def pytest_sessionstart() -> None:
    """Ensure sockets are enabled early on Windows.

    Some session-scoped fixtures create an event loop before per-test hooks run.
    """
    if sys.platform.startswith("win"):
        import pytest_socket  # noqa: PLC0415

        pytest_socket.enable_socket()

