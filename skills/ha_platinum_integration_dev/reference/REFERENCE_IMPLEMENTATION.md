# Reference Implementation Example (Mode A — Full Integration)

This reference shows a platinum-grade custom integration pattern for a REST API that provides fuel prices.

## Domain

`fuel_prices`

## File tree (canonical)

```
custom_components/fuel_prices/
  __init__.py
  manifest.json
  config_flow.py
  coordinator.py
  api.py
  const.py
  sensor.py
  diagnostics.py
  strings.json
  translations/en.json
  tests/
    __init__.py
    conftest.py
    test_config_flow.py
    test_coordinator.py
    test_sensor.py
```

## `custom_components/fuel_prices/const.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Final

DOMAIN: Final = "fuel_prices"

CONF_BASE_URL: Final = "base_url"
CONF_API_KEY: Final = "api_key"
CONF_STATION_ID: Final = "station_id"

DEFAULT_BASE_URL: Final = "https://api.example.com"
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=10)

PLATFORMS: Final = ["sensor"]

DATA_COORDINATOR: Final = "coordinator"


@dataclass(frozen=True, slots=True)
class FuelPricesConfig:
    base_url: str
    api_key: str
    station_id: str
```

## `custom_components/fuel_prices/manifest.json`

```json
{
  "domain": "fuel_prices",
  "name": "Fuel Prices",
  "codeowners": [],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://example.invalid",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://example.invalid/issues",
  "requirements": [],
  "version": "1.0.0"
}
```

## `custom_components/fuel_prices/api.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import aiohttp


class ApiError(Exception):
    """Base class for API failures."""


class ApiAuthError(ApiError):
    """Authentication/authorization failure."""


class ApiConnectionError(ApiError):
    """Network/connection failure."""


class ApiRateLimitError(ApiError):
    """Rate limited by server."""


@dataclass(frozen=True, slots=True)
class FuelPrice:
    fuel: str
    price: float
    currency: str


@dataclass(frozen=True, slots=True)
class StationPrices:
    station_id: str
    updated_at: str
    prices: tuple[FuelPrice, ...]


_TIMEOUT: Final = aiohttp.ClientTimeout(total=20)


class FuelPricesApiClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_key: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def async_get_station_prices(self, station_id: str) -> StationPrices:
        url = f"{self._base_url}/v1/stations/{station_id}/prices"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with self._session.get(url, headers=headers, timeout=_TIMEOUT) as resp:
                if resp.status in (401, 403):
                    raise ApiAuthError("Unauthorized")
                if resp.status == 429:
                    raise ApiRateLimitError("Rate limited")
                if resp.status >= 500:
                    raise ApiError(f"Server error ({resp.status})")
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
        except aiohttp.ClientResponseError as err:
            raise ApiError(f"HTTP error: {err.status}") from err
        except aiohttp.ClientConnectionError as err:
            raise ApiConnectionError("Connection error") from err
        except aiohttp.ClientError as err:
            raise ApiError("Client error") from err

        prices_raw = data.get("prices")
        if not isinstance(prices_raw, list):
            raise ApiError("Invalid payload: prices")

        prices: list[FuelPrice] = []
        for item in prices_raw:
            if not isinstance(item, dict):
                continue
            fuel = item.get("fuel")
            price = item.get("price")
            currency = item.get("currency", "USD")
            if not isinstance(fuel, str) or not isinstance(price, (int, float)) or not isinstance(currency, str):
                continue
            prices.append(FuelPrice(fuel=fuel, price=float(price), currency=currency))

        station = data.get("station_id", station_id)
        updated_at = data.get("updated_at", "")
        if not isinstance(station, str) or not isinstance(updated_at, str):
            raise ApiError("Invalid payload: metadata")

        return StationPrices(station_id=station, updated_at=updated_at, prices=tuple(prices))
```

## `custom_components/fuel_prices/coordinator.py`

```python
from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ApiAuthError,
    ApiConnectionError,
    ApiError,
    ApiRateLimitError,
    FuelPricesApiClient,
    StationPrices,
)
from .const import DEFAULT_SCAN_INTERVAL


class FuelPricesCoordinator(DataUpdateCoordinator[StationPrices]):
    _NAME: Final = "fuel_prices"

    def __init__(
        self,
        hass: HomeAssistant,
        client: FuelPricesApiClient,
        station_id: str,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass=hass,
            logger=__import__("logging").getLogger(__name__),
            name=self._NAME,
            update_interval=update_interval,
        )
        self._client = client
        self._station_id = station_id

    async def _async_update_data(self) -> StationPrices:
        try:
            return await self._client.async_get_station_prices(self._station_id)
        except ApiAuthError as err:
            raise UpdateFailed("Authentication failed") from err
        except ApiRateLimitError as err:
            raise UpdateFailed("Rate limited") from err
        except ApiConnectionError as err:
            raise UpdateFailed("Connection error") from err
        except ApiError as err:
            raise UpdateFailed("API error") from err
```

## `custom_components/fuel_prices/__init__.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FuelPricesApiClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_STATION_ID,
    DATA_COORDINATOR,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FuelPricesConfig,
    PLATFORMS,
)
from .coordinator import FuelPricesCoordinator


@dataclass(slots=True)
class FuelPricesRuntimeData:
    config: FuelPricesConfig
    coordinator: FuelPricesCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    base_url: str = entry.data[CONF_BASE_URL]
    api_key: str = entry.data[CONF_API_KEY]
    station_id: str = entry.data[CONF_STATION_ID]

    config = FuelPricesConfig(base_url=base_url, api_key=api_key, station_id=station_id)
    session = async_get_clientsession(hass)
    client = FuelPricesApiClient(session=session, base_url=base_url, api_key=api_key)

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = FuelPricesCoordinator(hass=hass, client=client, station_id=station_id, update_interval=scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = FuelPricesRuntimeData(
        config=config,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
```

## `custom_components/fuel_prices/config_flow.py`

```python
from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ApiAuthError, ApiConnectionError, ApiError, FuelPricesApiClient
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_STATION_ID,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


async def _async_validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    session = async_get_clientsession(hass)
    client = FuelPricesApiClient(
        session=session,
        base_url=str(data[CONF_BASE_URL]),
        api_key=str(data[CONF_API_KEY]),
    )
    await client.async_get_station_prices(str(data[CONF_STATION_ID]))


class FuelPricesConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate_input(self.hass, user_input)
            except ApiAuthError:
                errors["base"] = "auth"
            except ApiConnectionError:
                errors["base"] = "cannot_connect"
            except ApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_BASE_URL]}::{user_input[CONF_STATION_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Fuel Prices", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_STATION_ID): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None

        if user_input is not None:
            new_data = {
                **self._reauth_entry.data,
                CONF_API_KEY: user_input[CONF_API_KEY],
            }
            try:
                await _async_validate_input(self.hass, new_data)
            except ApiAuthError:
                errors["base"] = "auth"
            except ApiConnectionError:
                errors["base"] = "cannot_connect"
            except ApiError:
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(self._reauth_entry, data=new_data)
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema({vol.Required(CONF_API_KEY): str})
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        return FuelPricesOptionsFlow(config_entry)


class FuelPricesOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if isinstance(current, timedelta):
            current_minutes = int(current.total_seconds() // 60)
        else:
            current_minutes = int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60)

        schema = vol.Schema(
            {
                vol.Required("scan_interval_minutes", default=current_minutes): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=120)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_finish(self, user_input: dict[str, Any]):
        return self.async_create_entry(
            title="",
            data={CONF_SCAN_INTERVAL: timedelta(minutes=int(user_input["scan_interval_minutes"]))},
        )
```

## `custom_components/fuel_prices/sensor.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FuelPricesCoordinator


@dataclass(frozen=True, slots=True)
class FuelSensorDescription:
    key: str
    name: str
    fuel: str


SENSORS: Final[tuple[FuelSensorDescription, ...]] = (
    FuelSensorDescription(key="unleaded", name="Unleaded", fuel="unleaded"),
    FuelSensorDescription(key="diesel", name="Diesel", fuel="diesel"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    coordinator: FuelPricesCoordinator = runtime.coordinator

    async_add_entities([FuelPriceSensor(coordinator, entry.entry_id, d) for d in SENSORS])


class FuelPriceSensor(CoordinatorEntity[FuelPricesCoordinator], SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "USD"

    def __init__(self, coordinator: FuelPricesCoordinator, entry_id: str, description: FuelSensorDescription) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self.entity_description = description
        self._attr_name = f"Fuel Price {description.name}"
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Fuel Station",
            manufacturer="Example",
            model="Fuel Prices API",
        )

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if data is None:
            return None
        for price in data.prices:
            if price.fuel == self.entity_description.fuel:
                self._attr_native_unit_of_measurement = price.currency
                return price.price
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        data = self.coordinator.data
        if data is None:
            return {}
        return {"updated_at": data.updated_at, "station_id": data.station_id}
```

## `custom_components/fuel_prices/diagnostics.py`

```python
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.redact import async_redact_data

from .const import CONF_API_KEY, DOMAIN

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    devices = dr.async_entries_for_config_entry(device_reg, entry.entry_id)
    entities = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "devices": [d.as_dict() for d in devices],
        "entities": [e.as_dict() for e in entities],
    }
```

## `custom_components/fuel_prices/strings.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Fuel Prices",
        "description": "Configure access to your fuel prices API.",
        "data": {
          "base_url": "Base URL",
          "api_key": "API key",
          "station_id": "Station ID"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate",
        "data": {
          "api_key": "API key"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect.",
      "auth": "Authentication failed.",
      "unknown": "Unexpected error."
    },
    "abort": {
      "already_configured": "This station is already configured.",
      "reauth_successful": "Re-authentication was successful."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Options",
        "data": {
          "scan_interval_minutes": "Update interval (minutes)"
        }
      }
    }
  }
}
```

## `custom_components/fuel_prices/translations/en.json`

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Fuel Prices",
        "description": "Configure access to your fuel prices API.",
        "data": {
          "base_url": "Base URL",
          "api_key": "API key",
          "station_id": "Station ID"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate",
        "data": {
          "api_key": "API key"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect.",
      "auth": "Authentication failed.",
      "unknown": "Unexpected error."
    },
    "abort": {
      "already_configured": "This station is already configured.",
      "reauth_successful": "Re-authentication was successful."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Options",
        "data": {
          "scan_interval_minutes": "Update interval (minutes)"
        }
      }
    }
  }
}
```

## `custom_components/fuel_prices/tests/conftest.py`

```python
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_api_client() -> Generator[AsyncMock]:
    client = AsyncMock()
    yield client
```

## `custom_components/fuel_prices/tests/test_config_flow.py`

```python
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from custom_components.fuel_prices.const import CONF_API_KEY, CONF_BASE_URL, CONF_STATION_ID, DOMAIN


@pytest.mark.asyncio
async def test_config_flow_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] == "form"

    with patch(
        "custom_components.fuel_prices.config_flow.FuelPricesApiClient.async_get_station_prices",
        new=AsyncMock(),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_BASE_URL: "https://api.example.com",
                CONF_API_KEY: "token",
                CONF_STATION_ID: "station-1",
            },
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Fuel Prices"
    assert result2["data"][CONF_STATION_ID] == "station-1"


@pytest.mark.asyncio
async def test_config_flow_auth_error(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    from custom_components.fuel_prices.api import ApiAuthError

    with patch(
        "custom_components.fuel_prices.config_flow.FuelPricesApiClient.async_get_station_prices",
        side_effect=ApiAuthError("bad"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_BASE_URL: "https://api.example.com",
                CONF_API_KEY: "bad",
                CONF_STATION_ID: "station-1",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "auth"
```

## `custom_components/fuel_prices/tests/test_coordinator.py`

```python
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.fuel_prices.api import ApiConnectionError, StationPrices
from custom_components.fuel_prices.coordinator import FuelPricesCoordinator


@pytest.mark.asyncio
async def test_coordinator_update_success(hass: HomeAssistant) -> None:
    client = AsyncMock()
    client.async_get_station_prices.return_value = StationPrices(
        station_id="s1", updated_at="2026-01-01T00:00:00Z", prices=tuple()
    )

    coordinator = FuelPricesCoordinator(hass=hass, client=client, station_id="s1")
    data = await coordinator._async_update_data()
    assert data.station_id == "s1"


@pytest.mark.asyncio
async def test_coordinator_update_connection_error(hass: HomeAssistant) -> None:
    client = AsyncMock()
    client.async_get_station_prices.side_effect = ApiConnectionError("down")

    coordinator = FuelPricesCoordinator(hass=hass, client=client, station_id="s1")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
```

## `custom_components/fuel_prices/tests/test_sensor.py`

```python
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.fuel_prices.api import FuelPrice, StationPrices
from custom_components.fuel_prices.coordinator import FuelPricesCoordinator
from custom_components.fuel_prices.sensor import FuelPriceSensor, FuelSensorDescription


@pytest.mark.asyncio
async def test_sensor_value_from_coordinator(hass: HomeAssistant) -> None:
    client = AsyncMock()
    client.async_get_station_prices.return_value = StationPrices(
        station_id="s1",
        updated_at="2026-01-01T00:00:00Z",
        prices=(FuelPrice(fuel="unleaded", price=1.23, currency="USD"),),
    )

    coordinator = FuelPricesCoordinator(hass=hass, client=client, station_id="s1")
    await coordinator.async_refresh()

    desc = FuelSensorDescription(key="unleaded", name="Unleaded", fuel="unleaded")
    entity = FuelPriceSensor(coordinator, entry_id="entry1", description=desc)
    assert entity.native_value == 1.23
```
