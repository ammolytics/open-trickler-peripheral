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

import gpiozero # pylint: disable=import-error;


class TricklerMotor:
    """Controls a small vibration DC motor with the PWM controller on the Pi."""

    def __init__(self, config, **kwargs):
        """Constructor."""
        # Store memcache client if provided.
        self._memcache = kwargs.get('memcache')
        # Pull default values from config, giving preference to provided arguments.
        self._constants = enum.Enum('memcache_vars', dict(config['memcache_vars']))

        self.motor_pin = kwargs.get('motor_pin', config['motors']['trickler_pin'])
        self.min_pwm = kwargs.get('min_pwm', config['motors']['trickler_min_pwm'])
        self.max_pwm = kwargs.get('max_pwm', config['motors']['trickler_max_pwm'])

        self.pwm = gpiozero.PWMOutputDevice(self.motor_pin)
        logging.debug(
            'Created pwm motor on PIN %r with min %r and max %r: %r',
            self.motor_pin,
            self.min_pwm,
            self.max_pwm,
            self.pwm)
        atexit.register(self._graceful_exit)

    def _graceful_exit(self):
        """Graceful exit function, turn off motor and close GPIO pin."""
        logging.debug('Closing trickler motor...')
        self.pwm.off()
        self.pwm.close()

    def update(self, target_pwm):
        """Change PWM speed of motor (int), enforcing clamps."""
        logging.debug('Updating target_pwm to %r', target_pwm)
        target_pwm = max(min(int(target_pwm), self.max_pwm), self.min_pwm)
        logging.debug('Adjusted clamped target_pwm to %r', target_pwm)
        self.set_speed(target_pwm / 100)

    def set_speed(self, speed):
        """Sets the PWM speed (float) and circumvents any clamps."""
        # Speed must be 0 - 1.
        if 0 <= speed <= 1:
            logging.debug('Setting speed from %r to %r', self.speed, speed)
            self.pwm.value = speed
            if self._memcache:
                self._memcache.set(self._constants.TRICKLER_MOTOR_SPEED, self.speed)
        else:
            logging.debug('invalid motor speed: %r must be between 0 and 1.', speed)

    def off(self):
        """Turns motor off."""
        self.set_speed(0)

    @property
    def speed(self):
        """Returns motor speed (float)."""
        return self.pwm.value


# Handle command-line execution.
if __name__ == '__main__':
    import argparse
    import configparser
    import time

    import helpers


    # Default argument values.
    DEFAULTS = dict(
        verbose = False,
    )

    parser = argparse.ArgumentParser(description='Test motors.')
    parser.add_argument('config_file')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--trickler_motor_pin', type=int)
    #parser.add_argument('--servo_motor_pin', type=int)
    parser.add_argument('--max_pwm', type=float)
    parser.add_argument('--min_pwm', type=float)
    args = parser.parse_args()

    # Parse the config file.
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(args.config_file)

    # Order of priority is 1) command-line argument, 2) config file, 3) default.
    kwargs = {}
    if args.verbose is not None:
        kwargs['verbose'] = args.verbose

    VERBOSE = DEFAULTS['verbose'] or config['general']['verbose']
    if args.verbose is not None:
        kwargs['verbose'] = args.verbose
        VERBOSE = args.verbose
    if args.trickler_motor_pin is not None:
        TRICKLER_MOTOR_PIN = args.trickler_motor_pin
        kwargs['trickler_motor_pin'] = args.trickler_motor_pin
    if args.max_pwm is not None:
        kwargs['max_pwm'] = args.max_pwm
    if args.min_pwm is not None:
        kwargs['min_pwm'] = args.min_pwm

    # Configure Python logging.
    LOG_LEVEL = logging.INFO
    if VERBOSE:
        LOG_LEVEL = logging.DEBUG
    helpers.setup_logging(LOG_LEVEL)

    # Setup memcache.
    memcache_client = helpers.get_mc_client()

    # Create a TricklerMotor instance and then run it at different speeds.
    motor = TricklerMotor(
        config=config,
        memcache=memcache_client,
        **kwargs)
    print('Spinning up trickler motor in 3 seconds...')
    time.sleep(3)
    for x in range(1, 101):
        motor.set_speed(x / 100)
        time.sleep(.05)
    for x in range(100, 0, -1):
        motor.set_speed(x / 100)
        time.sleep(.05)
    motor.off()
    print('Done.')
