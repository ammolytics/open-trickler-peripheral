#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""

import datetime
import decimal
import enum
import logging
import time

import helpers
import PID
import motors
import scales


# Components:
# 0. Server (Pi)
# 1. Scale (serial)
# 2. Trickler (gpio/PWM)
# 3. Dump (gpio/servo?)
# 4. API
# 6. Bluetooth?
# 7: Powder pan/cup?

# TODO
# - handle case where scale is booted with pan on -- shows error instead of negative value
# - detect scale that's turned off (blank values)
# - validate inputs (target weight)


def trickler_loop(memcache, constants, pid, trickler_motor, scale, target_weight, target_unit, pidtune_logger): # pylint: disable=too-many-arguments;
    """Main trickler control loop run when all devices are ready, target weight is set, and auto-mode is on."""
    pidtune_logger.info('timestamp, input (motor %), output (weight %)')
    logging.info('Starting trickling process...')

    # Note(eric): All `break` calls will exit the loop and this function.
    while 1:
        # Stop running if auto mode is disabled.
        if not memcache.get(constants.AUTO_MODE.value):
            logging.debug('auto mode disabled.')
            break

        # Read scale values (weight/unit/stable)
        scale.update()

        # Stop running if scale's unit no longer matches target unit.
        if scale.unit != target_unit:
            logging.debug('Target unit does not match scale unit.')
            break

        # Stop running if pan removed.
        if scale.weight < 0:
            logging.debug('Pan removed.')
            break

        remainder_weight = target_weight - scale.weight
        logging.debug('remainder_weight: %r', remainder_weight)

        pidtune_logger.info(
            '%s, %s, %s',
            datetime.datetime.now().timestamp(),
            trickler_motor.speed,
            scale.weight / target_weight)

        # Trickling complete.
        if remainder_weight <= 0:
            logging.debug('Trickling complete, motor turned off and PID reset.')
            break

        # PID controller requires float value instead of decimal.Decimal
        pid.update(float(scale.weight / target_weight) * 100)
        trickler_motor.update(pid.output)
        logging.debug('trickler_motor.speed: %r, pid.output: %r', trickler_motor.speed, pid.output)
        logging.info(
            'remainder: %s %s scale: %s %s motor: %s',
            remainder_weight,
            target_unit,
            scale.weight,
            scale.unit,
            trickler_motor.speed)

    # Clean up tasks.
    trickler_motor.off()
    # Clear PID values.
    pid.clear()
    logging.info('Trickling process stopped.')


def main(config, memcache, args, pidtune_logger):
    """Main trickler function. This runs everything."""
    constants = enum.Enum('memcache_vars', config['memcache_vars'])

    # Set up the PID controller.
    pid = PID.PID(
        float(config['PID']['Kp']),
        float(config['PID']['Ki']),
        float(config['PID']['Kd']))
    logging.debug('pid: %r', pid)

    # Set up the trickler motor controller.
    trickler_motor = motors.TricklerMotor(config, memcache=memcache)
    logging.debug('trickler_motor: %r', trickler_motor)
    #servo_motor = gpiozero.AngularServo(int(config['motors']['servo_pin']))

    # Set up the scale controller.
    scale_cls = scales.SCALES[config['scale']['model']]
    scale = scale_cls(config, memcache=memcache)
    logging.debug('scale: %r', scale)

    # Set initial values in memcache.
    memcache.set_multi({
        constants.AUTO_MODE.value: args.auto_mode or False,
        constants.TARGET_WEIGHT.value: args.target_weight or decimal.Decimal('0.0'),
        constants.TARGET_UNIT.value: scale.unit_map.get(args.target_unit, 'GN'),
    })

    # Outer-most control loop for the whole trickler system.
    while 1:
        # Update settings from memcache.
        auto_mode = memcache.get(constants.AUTO_MODE.value)
        target_weight = memcache.get(constants.TARGET_WEIGHT.value)
        target_unit = memcache.get(constants.TARGET_UNIT.value)
        # Use percentages for PID control to avoid complexity w/ different units of weight.
        pid.SetPoint = 100.0
        scale.update()

        # Set scale to match target unit.
        if target_unit != scale.unit:
            logging.info('scale.unit: %r, target_unit: %r', scale.unit, target_unit)
            scale.change_unit()

        logging.info(
            'target: %s %s scale: %s %s auto_mode: %s',
            target_weight,
            target_unit,
            scale.weight,
            scale.unit,
            auto_mode)

        # Powder pan in place, scale stable, ready to trickle.
        if (scale.weight >= 0 and
                scale.weight < target_weight and
                scale.unit == target_unit and
                scale.is_stable and
                auto_mode):
            # Wait a second to start trickling.
            time.sleep(1)
            # Run trickler loop.
            trickler_loop(memcache, constants, pid, trickler_motor, scale, target_weight, target_unit, pidtune_logger)


if __name__ == '__main__':
    import argparse
    import configparser

    # Default argument values.
    DEFAULTS = dict(
        verbose = False,
    )

    parser = argparse.ArgumentParser(description='Run OpenTrickler.')
    parser.add_argument('config_file')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--auto_mode', action='store_true')
    parser.add_argument('--pid_tune', action='store_true')
    parser.add_argument('--target_weight', type=decimal.Decimal, default=0)
    parser.add_argument('--target_unit', choices=('g', 'GN'), default='GN')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.optionxform = str
    if args.config_file:
        config.read(args.config_file)

    # Order of priority is 1) command-line argument, 2) config file, 3) default.
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

    # Set up a separate logger for PID tuning with it's own format.
    pidtune_logger = logging.getLogger('pid_tune')
    pid_handler = logging.StreamHandler()
    pid_handler.setFormatter(logging.Formatter('%(message)s'))

    # Configure the log level based on if the tuner feature should be active.
    pidtune_logger.setLevel(logging.ERROR)
    if args.pid_tune or config['PID'].getboolean('pid_tuner_mode'):
        pidtune_logger.setLevel(logging.INFO)

    # Run the main trickler program.
    main(config, memcache_client, args, pidtune_logger)
