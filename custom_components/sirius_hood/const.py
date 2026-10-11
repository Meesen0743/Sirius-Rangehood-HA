"""Constants for the Sirius Range Hood integration."""

DOMAIN = "sirius_hood"
DEFAULT_NAME = "Sirius Range Hood"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15

# Cloud API Base
API_BASE_URL = "https://sirius.iotpga.it"

# MQTT broker (live device state)
MQTT_HOST = "sirius.iotpga.it"
MQTT_PORT = 8884
MQTT_TENANT = "codermine"

CAP_ONOFF = "device.onOff"
CAP_FAN_SPEED = "device.fanSpeed"
CAP_FAN_BOOST = "device.boostValue"
CAP_FAN_FLOW = "device.fanFlow"
CAP_FAN_POWER = "device.fanPower"
CAP_BIPOWER = "device.biPowerEnabled"

CAP_LIGHT_ONOFF = "device.lightOnOff"
CAP_LIGHT_BRIGHTNESS = "device.lightBrightness"
CAP_LIGHT_COLORTEMP = "device.lightColorTemperature"
CAP_LIGHT_POWER = "device.lightPower"

CAP_LIGHT2_ONOFF = "device.light2OnOff"
CAP_LIGHT2_BRIGHTNESS = "device.light2Brightness"
CAP_LIGHT2_COLORTEMP = "device.light2ColorTemperature"
CAP_LIGHT2_POWER = "device.light2Power"

CAP_CLEAN_AIR = "device.cleanAirEnabled"
CAP_AUTO_MODE = "device.autoModeEnabled"
CAP_QUALITY_AIR = "device.qualityAirEnabled"

CAP_CO2 = "device.co2"
CAP_IAQ = "device.iaq500"
CAP_TEMP = "device.temp"
CAP_HUM = "device.hum"

CAP_FILTER1_WORN = "device.filter1.worn"
CAP_FILTER1_VALUE = "device.filter1Value"
CAP_FILTER2_WORN = "device.filter2.worn"
CAP_FILTER2_VALUE = "device.filter2Value"
