"""
GO Plus + Interaction Controller

State machine that interprets LED commands from Pokemon GO and automatically
sends button presses to trigger catches and PokéStop spins.

Pokemon GO drives the LED to signal game events; the device responds with
button press notifications to act on them (catch attempt / spin).
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Optional

from .gatt_profile import LEDCommand, PATTERN_POKEMON_NEARBY, PATTERN_POKESTOP_NEARBY
from .peripheral import GOPlusPeripheral
from . import config

logger = logging.getLogger(__name__)


class DeviceState(Enum):
    IDLE            = auto()
    POKEMON_NEARBY  = auto()
    CATCHING        = auto()
    CATCH_SUCCESS   = auto()
    CATCH_FAIL      = auto()
    POKESTOP_NEARBY = auto()
    SPINNING        = auto()
    SPIN_SUCCESS    = auto()
    SPIN_FAIL       = auto()


class GOPlusController:
    """
    Drives the peripheral in response to LED commands from Pokemon GO.

    Auto-catch and auto-spin are enabled by default. Set auto_catch=False
    or auto_spin=False to disable them (manual button use only).
    """

    def __init__(self, peripheral: GOPlusPeripheral):
        self.peripheral  = peripheral
        self.state       = DeviceState.IDLE
        self.auto_catch  = True
        self.auto_spin   = True
        self._pending_task: Optional[asyncio.Task] = None
        peripheral.on_led_command(self._on_led_command)

    def _on_led_command(self, cmd: LEDCommand):
        pattern_id = cmd.pattern_id()
        new_state = self._classify(pattern_id)
        if new_state != self.state:
            self._transition(new_state)

    def _classify(self, pattern_id: int) -> DeviceState:
        if pattern_id in PATTERN_POKEMON_NEARBY:
            return DeviceState.POKEMON_NEARBY
        if pattern_id in PATTERN_POKESTOP_NEARBY:
            return DeviceState.POKESTOP_NEARBY
        # Catch/spin outcomes are logged but don't trigger button presses
        return DeviceState.IDLE

    def _transition(self, new_state: DeviceState):
        logger.info("State: %s → %s", self.state.name, new_state.name)
        self.state = new_state

        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()

        if new_state in (DeviceState.POKEMON_NEARBY, DeviceState.POKESTOP_NEARBY):
            self._pending_task = asyncio.create_task(self._act(new_state))

    async def _act(self, trigger: DeviceState):
        if trigger == DeviceState.POKEMON_NEARBY and not self.auto_catch:
            return
        if trigger == DeviceState.POKESTOP_NEARBY and not self.auto_spin:
            return

        delay = (config.AUTO_CATCH_DELAY_S if trigger == DeviceState.POKEMON_NEARBY
                 else config.AUTO_SPIN_DELAY_S)
        hold  = config.BUTTON_HOLD_MS / 1000.0

        logger.debug("Waiting %.1fs before button press", delay)
        await asyncio.sleep(delay)
        await self.peripheral.send_button_press()
        await asyncio.sleep(hold)
        await self.peripheral.send_button_release()
        logger.info("Button press sent for %s", trigger.name)

    async def manual_press(self):
        """Manually trigger a single button press (for testing)."""
        await self.peripheral.send_button_press()
        await asyncio.sleep(config.BUTTON_HOLD_MS / 1000.0)
        await self.peripheral.send_button_release()
