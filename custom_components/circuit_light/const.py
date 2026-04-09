from homeassistant.const import Platform

DOMAIN = "circuit_light"
PLATFORMS = [Platform.LIGHT]

CONF_NAME = "name"
CONF_POWER_ENTITY = "power_entity"
CONF_BULB_ENTITIES = "bulb_entities"

DATA_KEY = DOMAIN