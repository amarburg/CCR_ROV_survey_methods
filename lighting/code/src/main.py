"""
Main application for the Lutris Lighting System.
Controls 4 SeaLite LED lights via PWM input from BlueROV servo output.
Monitors power via INA238.
"""

import time
from machine import Pin, I2C

import sys
import os

# Add lib to path - works for both mpremote mount (/remote) and deployed (/)
if '/remote' in os.getcwd():
    sys.path.insert(0, '/remote/lib')
else:
    sys.path.insert(0, '/lib')

from uart_wrapper import UARTWrapper
from pwm_reader import PWMReader

from ina238 import INA238
from pydspl_seasense.sealite import Sealite


from config import Config

try:
    print("Loading local config from local_config.py")
    import local_config
except ImportError:
    pass

class LightingController:
    """
    Main controller for the Lutris lighting system.

    Manages 4 SeaLite LED lights on a shared UART0 bus,
    addressed individually (1-4) via the SeaSense protocol.
    Light brightness is controlled by a PWM input from the BlueROV.
    """


    def __init__(self):
        """Initialize the lighting controller."""
        self._uart = None
        self._lights = []
        self._power_monitor = None
        self._pwm_reader = None
        self._current_level = 0

        self._init_uart()
        self._init_lights()
        self._init_power_monitor()
        self._init_pwm_reader()

    def _init_uart(self):
        """Initialize shared UART0 connection."""
        self._uart = UARTWrapper(
            uart_id=Config.RS485_UART,
            baudrate=Config.BAUDRATE,
            tx_control_pin=Config.RS485_RTS_PIN,
            timeout=Config.UART_TIMEOUT_MS
        )

        print(f"UART{Config.RS485_UART} initialized on default pins")


    def _init_lights(self):
        """Initialize SeaLite objects for each light."""
        for addr in Config.LIGHT_ADDRESSES:
            light = Sealite(address=addr, max_level=100, expect_response=True)
            self._lights.append(light)
        print(f"Initialized {len(self._lights)} SeaLite lights (addresses {Config.LIGHT_ADDRESSES})")

    def _init_power_monitor(self):
        """Initialize I2C and INA238 power monitor."""
        i2c = I2C(
            Config.I2C_ID,
            sda=Pin(Config.I2C_SDA_PIN),
            scl=Pin(Config.I2C_SCL_PIN),
            freq=400000
        )

        devices = i2c.scan()
        print(f"I2C devices found: {[hex(d) for d in devices]}")

        try:
            self._power_monitor = INA238(
                i2c,
                address=Config.INA238_ADDRESS,
                shunt_ohms=Config.SHUNT_RESISTANCE,
                max_current=Config.MAX_CURRENT
            )
            print("INA238 power monitor initialized")
        except RuntimeError as e:
            print(f"Warning: INA238 not found: {e}")
            self._power_monitor = None

    def _init_pwm_reader(self):
        """Initialize PWM input reader."""
        self._pwm_reader = PWMReader(
            Config.PWM_INPUT_PIN,
            valid_min_us=Config.PWM_VALID_MIN_US,
            valid_max_us=Config.PWM_VALID_MAX_US,
        )
        print(f"PWM input initialized: GP{Config.PWM_INPUT_PIN}")
        print(f"  PWM range: {Config.PWM_MIN_US}-{Config.PWM_MAX_US} us -> 0-100% brightness")
        print(f"  Accept range: {Config.PWM_VALID_MIN_US}-{Config.PWM_VALID_MAX_US} us, median window: {Config.MEDIAN_WINDOW}")

    def pwm_to_level(self, pulse_width_us):
        """Map PWM pulse width (us) to light level (0-100)."""
        if pulse_width_us <= Config.PWM_MIN_US:
            return 0
        if pulse_width_us >= Config.PWM_MAX_US:
            return 100
        return int((pulse_width_us - Config.PWM_MIN_US) * 100
                    / (Config.PWM_MAX_US - Config.PWM_MIN_US))


    def light_at(self,i):
        if light_index < 0 or light_index >= len(self._lights):
            return None

        return lights[i]

    def set_light_level(self, light, level):
        """
        Set brightness level for a specific light.

        Args:
            light_index: Light index (0-3)
            level: Brightness level (0-100)

        Returns:
            True on success, False on failure
        """
        if isinstance(light, int):
            light = self.light_at(light)

        level = 0

        try:
            return light.set_level(self._uart, level)
        except Exception as e:
            print(f"Error setting light {light._address}: {e}")
            return False

    def set_all_lights(self, level):
        """Set brightness level for all lights."""
        success = 0

        print('DBG: LOUT       {level}')

        for light in self._lights:
            if self.set_light_level(light, level):
                success += 1

            # Arbitrary pause to let each light respond
            # This could either be tuned to better match the
            # actual time to respond, or the code to catch
            # replies from the lights could be made more robust.
            #time.sleep_us(50000)
            #
            # This is only necessary if we _aren't_ waiting for the 
            # light's response
        return success

    def get_light_level(self, light):
        """Read current brightness level from a light."""

        if isinstance(light, int):
            light = self.light_at(light)

        try:
            return light.read_level(self._uart)
        except Exception as e:
            print(f"Error reading light {light_index}: {e}")
            return None

    def dump_all_lights_info(self):
        for light in self._lights:
            try:
                self.print_from_light(light,f'Info:     {light.read_info(self._uart)}')
            except Exception as e:
                print(f'Exception getting info from light {light._address}: {e}')
                pass

    def dump_all_lights_stat(self):
        for light in self._lights:
            try:
                result = light.read_stat(self._uart)
                for r in result:
                    self.print_from_light(light,f'Stat:     {r}')    
                
                self.print_from_light(light,f'Level:    {light.read_level(self._uart)}')
                self.print_from_light(light,f'Temp:     {light.read_temperature(self._uart)}')
                self.print_from_light(light,f'Humidity: {light.read_humidity(self._uart)}')
            except Exception as e:
                print(f'Exception getting status from light {light._address}: {e}')
                pass

    def print_from_light(self,light,str):
        print(f'{time.time_ns():10} {light._address:-3}: {str}')

    def read_power(self):
        """Read power consumption from INA238."""
        if self._power_monitor is None:
            return None

        try:
            return self._power_monitor.read_all()
        except Exception as e:
            print(f"Error reading power: {e}")
            return None

    def all_off(self):
        """Turn off all lights."""
        return self.set_all_lights(0)

    def status(self):
        """Get status of all lights and power consumption."""
        return {
            'lights': [
                {'index': i, 'level': self._lights[i].level}
                for i in range(len(self._lights))
            ],
            'power': self.read_power()
        }

    def run(self):
        """Main control loop. Reads PWM input and updates light brightness.

        Runs until KeyboardInterrupt (Ctrl-C). Turns lights off on exit.
        """

        last_status_ms = time.ticks_ms()
        pw_samples = []

        try:
            print("Info from all lights:")
            print("=====================")
            self.dump_all_lights_info()
            print()

            print("PWM control loop running (Ctrl-C to stop)")


            while True:
                signal_age = self._pwm_reader.signal_age_ms
                signal_lost = (signal_age < 0 or
                               signal_age > self.SIGNAL_TIMEOUT_MS)

                if signal_lost:
                    pw_samples = []
                    pw_filtered = 0
                    target_level = 0
                else:
                    pw_samples.append(self._pwm_reader.pulse_width_us)
                    if len(pw_samples) > Config.MEDIAN_WINDOW:
                        pw_samples.pop(0)
                    pw_filtered = sorted(pw_samples)[len(pw_samples) // 2]
                    target_level = self.pwm_to_level(pw_filtered)

                # Only update lights if level changed beyond deadband
                if abs(target_level - self._current_level) >= Config.LEVEL_DEADBAND:
                    self.set_all_lights(target_level)
                    self._current_level = target_level

                # Periodic status output
                now_ms = time.ticks_ms()
                if time.ticks_diff(now_ms, last_status_ms) >= Config.STATUS_INTERVAL_MS:

                    self.dump_all_lights_stat()

                    if signal_lost:
                        print(f"PWM: NO SIGNAL | Level: {self._current_level}%")
                    else:
                        print(f"PWM: {pw_filtered} us | Level: {self._current_level}%")
                    last_status_ms = now_ms

                time.sleep_ms(Config.LOOP_INTERVAL_MS)

        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.all_off()
            self._pwm_reader.deinit()
            print("Lights off. PWM reader disabled.")


controller = None


def main():
    """Main entry point. Initializes controller and starts PWM control loop."""
    global controller

    print("Lutris Lighting System Starting...")
    print("-" * 40)

    controller = LightingController()

    print("-" * 40)
    print("REPL commands (if loop is stopped):")
    print("  c.set_all_lights(50)  # Manual override")
    print("  c.all_off()")
    print("  c.read_power()")
    print("  c.status()")
    print("-" * 40)

    controller.run()

    return controller


if __name__ == "__main__":
    main()
