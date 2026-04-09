from homeassistant.const import Platform

DOMAIN = "circuit_light"
PLATFORMS = [Platform.LIGHT]

CONF_NAME = "name"
CONF_POWER_ENTITY = "power_entity"
CONF_BULB_ENTITIES = "bulb_entities"
CONF_HIDE_CHILD_ENTITIES = "hide_child_entities"

DATA_KEY = DOMAIN

# Light attribute keys (avoid importing removed constants from HA internals).
# Home Assistant has been migrating color temperature from mireds ("color_temp")
# to kelvin ("color_temp_kelvin"). We support both for compatibility.
ATTR_COLOR_TEMP_MIREDS = "color_temp"
ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"
