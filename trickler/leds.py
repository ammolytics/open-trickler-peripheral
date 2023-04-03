#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""

import atexit
import enum
import logging
import time

import gpiozero # pylint: disable=import-error;

import helpers


class TricklerStatus(enum.Enum):
    """The tuple values correspond to auto_mode, motor_on."""
    READY = (False, False)
    RUNNING = (True, True)
    DONE = (True, False)


# Mapping of ready states to the corrresponding config file references which name the blink style to use.
STATUS_MAP = {
    TricklerStatus.READY: 'ready_status_led_mode',
    TricklerStatus.RUNNING: 'running_status_led_mode',
    TricklerStatus.DONE: 'done_status_led_mode',
}


def led_fast_blink(led):
    """Blink the LED fast."""
    led.blink(on_time=0.75, off_time=0.75)


def led_slow_blink(led):
    """Blink the LED slow."""
    led.blink(on_time=1.5, off_time=1.5)


def led_off(led):
    """Turn the LED off."""
    led.off()


def led_on(led):
    """Turn the LED on (solid)."""
    led.on()


def led_pulse(led):
    """Pulse the LED (built-in)."""
    led.pulse()


# Mapping of LED blink modes to function names.
LED_MODES = {
    'fast_blink': led_fast_blink,
    'off': led_off,
    'on': led_on,
    'pulse': led_pulse,
    'slow_blink': led_slow_blink,
}


def all_variables_set(memcache, constants):
    """Validation function to assert that the expected trickler variables are set (not None) before operating."""
    variables = (
        memcache.get(constants.AUTO_MODE, None) is not None,
        memcache.get(constants.TRICKLER_MOTOR_SPEED, None) is not None,
    )
    logging.info('Variables: %r', variables)
    return all(variables)


def graceful_exit(status_led):
    """Graceful exit function, turn off LEDs and close GPIO pin."""
    logging.debug('Closing LED pins...')
    status_led.off()
    status_led.close()


def run(config, memcache, args):
    """Main LED control loop."""
    # Turn this feature off if configured to do so.
    if config['leds'].getboolean('enable_status_leds') is False:
        return

    constants = enum.Enum('memcache_vars', config['memcache_vars'])

    last_led_fn = None
    status_led_pin = int(config['leds']['status_led_pin'])
    active_high = config['leds'].getboolean('active_high', True)
    status_led = gpiozero.PWMLED(status_led_pin, active_high=active_high)
    atexit.register(graceful_exit, status_led=status_led)

    logging.info('Checking if ready to begin...')
    while 1:
        if all_variables_set(memcache, constants):
            logging.info('Ready!')
            break
        time.sleep(0.1)

    while 1:
        try:
            motor_on = float(memcache.get(constants.TRICKLER_MOTOR_SPEED, 0.0)) > 0
            auto_mode = memcache.get(constants.AUTO_MODE)
        except (KeyError, ValueError):
            logging.exception('Possible cache miss, trying again.')
            break

        try:
            status = TricklerStatus((auto_mode, motor_on))
        except ValueError:
            logging.info('Bad state. auto_mode:%r and motor_on:%r', auto_mode, motor_on)
            break

        led_fn = LED_MODES.get(config['leds'][STATUS_MAP[status]])
        if led_fn != last_led_fn:
            led_fn(status_led)
            last_led_fn = led_fn
        time.sleep(1)


# Handle command-line execution.
if __name__ == '__main__':
    import argparse
    import configparser


    # Default argument values.
    DEFAULTS = dict(
        verbose = False,
    )

    parser = argparse.ArgumentParser(description='Test bluetooth')
    parser.add_argument('config_file')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    # Parse the config file.
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(args.config_file)

    VERBOSE = DEFAULTS['verbose'] or config['general']['verbose']
    if args.verbose is not None:
        VERBOSE = args.verbose

    # Configure Python logging.
    LOG_LEVEL = logging.INFO
    if VERBOSE:
        LOG_LEVEL = logging.DEBUG
    helpers.setup_logging(LOG_LEVEL)

    # Setup memcache.
    memcache_client = helpers.get_mc_client()

    # Run the main LED control loop.
    run(config, memcache_client, args)
