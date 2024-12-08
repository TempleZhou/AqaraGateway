""" Aqara Gateway Alarm Control Panel """

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState
)

from . import DOMAIN, GatewayGenericDevice
from .core.gateway import Gateway
from .core.utils import Utils
from .core.shell import TelnetShell, TelnetShellE1, TelnetShellM2POE

ALARM_STATES = [AlarmControlPanelState.ARMED_HOME, AlarmControlPanelState.ARMED_AWAY,
                AlarmControlPanelState.ARMED_NIGHT, AlarmControlPanelState.DISARMED]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Aqara Gateway Alarm Control Panael platform."""
    def setup(gateway: Gateway, device: dict, attr: str):
        if Utils.gateway_alarm_mode_supported(device['model']):
            async_add_entities([AqaraGatewayAlarm(
                gateway, device, attr)], True)

    gateway: Gateway = hass.data[DOMAIN][config_entry.entry_id]
    gateway.add_setup('alarm_control_panel', setup)


async def async_unload_entry(hass, entry):
    # pylint: disable=unused-argument
    """ unload entry """
    return True


class AqaraGatewayAlarm(GatewayGenericDevice, AlarmControlPanelEntity):
    """Representation of a Aqara Gateway Alarm."""
    _attr_alarm_state = AlarmControlPanelState.DISARMED
    _state = None
    _shell = None

    def __init__(
        self,
        gateway,
        device,
        attr
    ):
        """Initialize the Alarm Panel."""
        device_name = Utils.get_device_name(device['model']).lower()
        if "e1" in device_name:
            self._shell = TelnetShellE1(gateway.host)
        elif (("m2 2022" in device_name) or ("m1s 2022" in device_name) or
                    ("m3" in device_name) or ("m1s gen2" in device_name) or ("v1" in device_name)):
            self._shell = TelnetShellM2POE(gateway.host)
        else:
            self._shell = TelnetShell(gateway.host)
        self._shell.login()
        self._get_state()
        super().__init__(gateway, device, attr)
        self._attr_supported_features = (AlarmControlPanelEntityFeature.ARM_HOME |
                AlarmControlPanelEntityFeature.ARM_AWAY | AlarmControlPanelEntityFeature.ARM_NIGHT)

    @property
    def should_poll(self):
        """return should poll."""
        if self._shell:
            return True
        return False

    @property
    def icon(self):
        """return icon."""
        return "mdi:shield-home"

    @property
    def supported_features(self):
        """Flag supported features."""
        return (AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY |
                AlarmControlPanelEntityFeature.ARM_NIGHT)

    @property
    def code_arm_required(self):
        """return code arm required."""
        return False

    async def async_added_to_hass(self):
        """add to hass."""

    async def async_will_remove_from_hass(self) -> None:
        """remove from hass."""

    def alarm_disarm(self, code=None):
        """Send disarm command."""
        self._set_state(3)

    def alarm_arm_home(self, code=None):
        """Send arm home command."""
        self._set_state(0)

    def alarm_arm_away(self, code=None):
        """Send arm away command."""
        self._set_state(1)

    def alarm_arm_night(self, code=None):
        """Send arm night command."""
        self._set_state(2)

    def _set_state(self, state):
        if state in range(0, 3):
            self._shell.set_prop('persist.app.arming_state', str(state))
            value = 'true'
            command = "-arm -g"
        else:
            value = 'false'
            command = "-arm -u"
        self._shell.set_prop('persist.app.arming_guard', value)
        self._shell.run_basis_cli(command)
        self._state = ALARM_STATES[state]
        self.schedule_update_ha_state()

    def _get_state(self):
        self._attr_alarm_state = AlarmControlPanelState.DISARMED
        raw = self._shell.get_prop('persist.app.arming_guard')
        if raw == 'true':
            raw = self._shell.get_prop('persist.app.arming_state')
            if raw is not ["0", "1", "2", "3"]:
                raw = self._shell.get_prop('persist.app.arming_state')
            try:
                self._state = ALARM_STATES[int(raw)]
            except:
                self._state = 0


    def update(self, *args):
        """Update the alarm status."""
        self._get_state()
        self.schedule_update_ha_state()
