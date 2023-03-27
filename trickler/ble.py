#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""

import atexit
import logging

import bluezero # pylint: disable=import-error;

import helpers


TRICKLER_UUID = '10000000-be5f-4b43-a49f-76f2d65c6e28'
AUTO_MODE_UUID = '10000005-be5f-4b43-a49f-76f2d65c6e28'
SCALE_STATUS_UUID = '10000002-be5f-4b43-a49f-76f2d65c6e28'
TARGET_WEIGHT_UUID = '10000004-be5f-4b43-a49f-76f2d65c6e28'
SCALE_UNIT_UUID = '10000003-be5f-4b43-a49f-76f2d65c6e28'
SCALE_WEIGHT_UUID = '10000001-be5f-4b43-a49f-76f2d65c6e28'


# Mapping of bluetooth characteristic settings.
CHARACTERISTICS = dict(
    auto_mode=dict(
        uuid=AUTO_MODE_UUID,
        flags=['read', 'write'],
        description='Start/stop automatic trickle mode',
    ),
    target_weight=dict(
        uuid=TARGET_WEIGHT_UUID,
        flags=['read', 'write'],
        description='Target powder weight',
    ),
    scale_status=dict(
        uuid=SCALE_STATUS_UUID,
        flags=['read', 'notify'],
        description='Reads the current stability status of the scale',
    ),
    scale_unit=dict(
        uuid=SCALE_UNIT_UUID,
        flags=['read', 'write', 'notify'],
        description='Reads the current weight unit of the scale',
    ),
    scale_weight=dict(
        uuid=SCALE_WEIGHT_UUID,
        flags=['read', 'notify'],
        description='Reads the current weight value of the scale',
    ),
)


def graceful_exit(opentrickler):
    """Graceful exit function, stop advertising and disconnect clients."""
    logging.info('Stopping OpenTrickler Bluetooth...')
    # Note(eric): Copied these calls from bluezero KeyboardInterrupt handler since it lacks shutdown.
    opentrickler.mainloop.quit()
    opentrickler.ad_manager.unregister_advertisement(opentrickler.advert)


def main(config, memcache, args):
    """Main Bluetooth control loop."""
    adapters = list(bluezero.adapter.Adapter.available())
    logging.info('Available bluetooth adapters: %s', adapters)

    adapter_address = adapters[0].address
    logging.info('First adapter address: %s', adapter_address)

    device_name = config['bluetooth']['name']
    opentrickler = bluezero.peripheral.Peripheral(adapter_address, local_name=device_name)

    atexit.register(graceful_exit, opentrickler)
    opentrickler.add_service(srv_id=1, uuid=TRICKLER_UUID, primary=True)
    for i, key, char in enumerate(CHARACTERISTICS.items(), start=1):
        logging.debug('Adding characteristic: %r', key)
        char['srv_id'] = 1
        char['chr_id'] = i
        char['notifying'] = 'notify' in char['flags']
        opentrickler.add_characteristic(**char)

    opentrickler.publish()


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

    # Run the main bluetooth control loop.
    main(config, memcache_client, args)
