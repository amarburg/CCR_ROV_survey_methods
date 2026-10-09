from machine import Pin

class Config:
    """
    Default configuration for "standard" Pico configuration.

    Local configuration overrides can be added by creating a file "local_config.py"
    with the format:

        from config import Config

        Config.LIGHT_ADDRESSES = [2]
        ...

    local_config.py should not be commited to git
    """

    # The RX/TX silkscreen on the QtPy corresponds to UART1
    # Use the default TX and RX pins for the UART
    RS485_UART = 0
    RS485_RTS_PIN = None

    # Time to wait for responses from lights 
    UART_TIMEOUT_MS = 500

    # PWM input on the "A0" pin, which is connected to RP2004 pin 38
    # Also PWM6B
    PWM_INPUT_PIN = Pin.cpu.GPIO29

    # ArduSub servo PWM range (microseconds)
    PWM_MIN_US = 1100
    PWM_MAX_US = 1900

    # Accept-range for raw pulse samples. Pulses outside this are treated
    # as EMI glitches and dropped by the PWM reader's ISR.
    PWM_VALID_MIN_US = 900
    PWM_VALID_MAX_US = 2100

    # Median filter window over raw samples, to reject single-sample
    # outliers that pass the ISR range gate.
    MEDIAN_WINDOW = 9

    # Signal loss timeout - lights off if no PWM edges for this long
    SIGNAL_TIMEOUT_MS = 1000

    # Minimum brightness change (%) before updating lights (deadband)
    LEVEL_DEADBAND = 5

    # Control loop interval
    LOOP_INTERVAL_MS = 50

    # Status print interval
    STATUS_INTERVAL_MS = 2000

    # I2C for INA238
    I2C_ID = 1
    I2C_SDA_PIN = 14  # GP14
    I2C_SCL_PIN = 15  # GP15

    # INA238 configuration
    INA238_ADDRESS = 0x40
    SHUNT_RESISTANCE = 0.1  # Ohms
    MAX_CURRENT = 10.0      # Amps

    # Serial configuration
    BAUDRATE = 9600

    # Light addresses on the shared bus
    LIGHT_ADDRESSES = [1, 2, 3, 4]