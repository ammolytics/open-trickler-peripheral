#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""

import atexit
import enum
import functools
import logging
import os
import time

import pybleno # pylint: disable=import-error;

import helpers


TRICKLER_UUID = '10000000-be5f-4b43-a49f-76f2d65c6e28'


class BasicCharacteristic(pybleno.Characteristic): # pylint: disable=too-many-instance-attributes;
    """Base class for bluetooth characteristics."""

    def __init__(self, *args, **kwargs):
        """Instantiate and store a few extra variables."""
        super().__init__(*args, **kwargs)
        self._maxValueSize = None # pylint: disable=invalid-name;
        self._memcache = None
        self._mc_key = None
        self._updateValueCallback = None # pylint: disable=invalid-name;
        self._send_fn = helpers.noop
        self._recv_fn = helpers.noop
        self.__value = None

    def onSubscribe(self, maxValueSize, updateValueCallback):
        """Register the callback functions when a bluetooth client subscribes to a characteristic for updates."""
        self._maxValueSize = maxValueSize # pylint: disable=invalid-name;
        self._updateValueCallback = updateValueCallback

    def onUnsubscribe(self):
        """Unhook the callbacks when the client unsubscribes from the characterstic."""
        self._maxValueSize = None
        self._updateValueCallback = None

    def onReadRequest(self, offset, callback):
        """Bluetooth client reads this characteristic."""
        if offset:
            callback(pybleno.Characteristic.RESULT_ATTR_NOT_LONG, None)
        else:
            data = self._send_fn(self.mc_value) # pylint: disable=assignment-from-none;
            callback(pybleno.Characteristic.RESULT_SUCCESS, data)

    @property
    def mc_value(self):
        """Make the internal value accessible as a readable property."""
        return self.__value # pylint: disable=unused-private-member

    @mc_value.setter
    def mc_value(self, value):
        """Setter function for the internal characteristic value."""
        if value == self.__value:
            return
        logging.info('Updating %s: from %r to %r', self._mc_key, self.__value, value)
        self.__value = value
        if self._updateValueCallback:
            self._updateValueCallback(self._send_fn(self.__value))

    def mc_get(self):
        """Retry mechanism for memcache. May no longer be needed."""
        for _ in range(2):
            try:
                value = self._memcache.get(self._mc_key)
            except (KeyError, ValueError):
                logging.exception('Cache miss.')
            else:
                break
        return value

    def mc_update(self):
        """Updates the internal value to match what's in memcache."""
        value = self.mc_get()
        self.mc_value = value


class AutoMode(BasicCharacteristic):
    """Bluetooth characteristic for if Auto Mode is on or off."""

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': '10000005-be5f-4b43-a49f-76f2d65c6e28',
            'properties': ['read', 'write'],
            'descriptors': [
                pybleno.Descriptor(dict(
                    uuid='2901',
                    value='Start/stop automatic trickle mode'
                ))],
            'value': False,
        })
        self._memcache = memcache
        self._mc_key = constants.AUTO_MODE.value
        self._updateValueCallback = None
        self._send_fn = helpers.bool_to_bytes
        self._recv_fn = helpers.bytes_to_bool
        self.__value = self.mc_get() # pylint: disable=unused-private-member

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        """Handle Bluetooth client change request for this characteristic."""
        if offset:
            callback(pybleno.Characteristic.RESULT_ATTR_NOT_LONG)
        elif len(data) != 1:
            callback(pybleno.Characteristic.RESULT_INVALID_ATTRIBUTE_LENGTH)
        else:
            value = self._recv_fn(data)
            logging.info('Changing %s to %r', self._mc_key, value)
            self._memcache.set(self._mc_key, value)
            # This will notify subscribers.
            self.mc_value = value
            callback(pybleno.Characteristic.RESULT_SUCCESS)


class ScaleStatus(BasicCharacteristic):
    """Bluetooth characteristic for the Scale Status, as mapped by the scale class."""

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': '10000002-be5f-4b43-a49f-76f2d65c6e28',
            'properties': ['read', 'notify'],
            'descriptors': [
                pybleno.Descriptor(dict(
                    uuid='2901',
                    value='Reads the current stability status of the scale'
                ))],
        })
        self._memcache = memcache
        self._mc_key = constants.SCALE_STATUS.value
        self._updateValueCallback = None
        self._send_fn = helpers.enum_to_bytes
        self._recv_fn = helpers.bytes_to_enum
        self.__value = self.mc_get() # pylint: disable=unused-private-member


class TargetWeight(BasicCharacteristic):
    """Bluetooth characteristic for the target weight value. """

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': '10000004-be5f-4b43-a49f-76f2d65c6e28',
            'properties': ['read', 'write'],
            'descriptors': [
                pybleno.Descriptor(dict(
                    uuid='2901',
                    value='Target powder weight'
                ))],
        })
        self._memcache = memcache
        self._mc_key = constants.TARGET_WEIGHT.value
        self._updateValueCallback = None
        self._send_fn = helpers.decimal_to_bytes
        self._recv_fn = helpers.bytes_to_decimal
        self.__value = self.mc_get() # pylint: disable=unused-private-member

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        """Handle Bluetooth client request to change this characteristic value."""
        if offset:
            callback(pybleno.Characteristic.RESULT_ATTR_NOT_LONG)
        elif len(data) == 0:
            callback(pybleno.Characteristic.RESULT_INVALID_ATTRIBUTE_LENGTH)
        else:
            value = self._recv_fn(data)
            logging.info('Changing %s to %r', self._mc_key, value)
            self._memcache.set(self._mc_key, value)
            # This will notify subscribers.
            self.mc_value = value
            callback(pybleno.Characteristic.RESULT_SUCCESS)


class ScaleUnit(BasicCharacteristic): # pylint: disable=too-many-instance-attributes;
    """Bluetooth characteristic for the unit setting on the scale."""

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': '10000003-be5f-4b43-a49f-76f2d65c6e28',
            'properties': ['read', 'write', 'notify'],
            'descriptors': [
                pybleno.Descriptor(dict(
                    uuid='2901',
                    value='Reads the current weight unit of the scale'
                ))],
        })
        self._memcache = memcache
        self._mc_key = constants.SCALE_UNIT.value
        self._write_mc_key = constants.TARGET_UNIT.value
        self._updateValueCallback = None
        self._send_fn = helpers.enum_to_bytes
        scale_units = None
        logging.info('Waiting for scale_units to populate in memcache...')
        while scale_units is None:
            scale_units = self._memcache.get(constants.SCALE_UNITS.value)
            logging.info('scale_units: %r', scale_units)

        # Pull unit mappings from memcache into a local Enum. Scale won't change, so neither will this.
        self._units_enum = enum.Enum('scale_units', scale_units)
        self._recv_fn = functools.partial(helpers.bytes_to_enum, self._units_enum)
        self.__value = self.mc_get() # pylint: disable=unused-private-member,unused-private-member

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        if offset:
            callback(pybleno.Characteristic.RESULT_ATTR_NOT_LONG)
        elif len(data) != 1:
            callback(pybleno.Characteristic.RESULT_INVALID_ATTRIBUTE_LENGTH)
        else:
            value = self._recv_fn(data)
            logging.info('Changing %s to %r', self._write_mc_key, value)
            # NOTE: Cannot set the scale unit directly, but can change the target unit.
            self._memcache.set(self._write_mc_key, value)
            # Notify subscribers.
            if self._updateValueCallback:
                self._updateValueCallback(data)
            callback(pybleno.Characteristic.RESULT_SUCCESS)


class ScaleWeight(BasicCharacteristic):
    """Bluetooth characteristic for the weight value on the scale."""

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': '10000001-be5f-4b43-a49f-76f2d65c6e28',
            'properties': ['read', 'notify'],
            'descriptors': [
                pybleno.Descriptor(dict(
                    uuid='2901',
                    value='Reads the current weight value of the scale'
                ))],
        })
        self._memcache = memcache
        self._mc_key = constants.SCALE_WEIGHT.value
        self._updateValueCallback = None
        self._send_fn = helpers.decimal_to_bytes
        self._recv_fn = helpers.bytes_to_decimal
        self.__value = self.mc_get() # pylint: disable=unused-private-member


class TricklerService(pybleno.BlenoPrimaryService):
    """Defines all of the characteristics avaliable for this device over Bluetooth."""

    def __init__(self, memcache, constants):
        """Constructor."""
        super().__init__({
            'uuid': TRICKLER_UUID,
            'characteristics': [
                AutoMode(memcache, constants),
                ScaleStatus(memcache, constants),
                ScaleUnit(memcache, constants),
                ScaleWeight(memcache, constants),
                TargetWeight(memcache, constants),
            ],
        })

    def all_mc_update(self):
        """Update all values in memcache."""
        for characteristic in self['characteristics']:
            characteristic.mc_update()


def error_handler(error):
    """Simple error handler function."""
    if error:
        logging.error(error)


def on_state_change(device_name, bleno, trickler_service, state):
    """Shared state change handler function."""
    if state == 'poweredOn':
        bleno.startAdvertising(device_name, [TRICKLER_UUID], error_handler)
    else:
        bleno.stopAdvertising()


def on_advertising_start(bleno, trickler_service, error):
    """Called when bluetooth starts advertising."""
    if error:
        logging.error(error)
    else:
        logging.info('Starting advertising')
        bleno.setServices([trickler_service])


def on_advertising_stop():
    """Called when bluetooth stops advertising."""
    logging.info('Stopping advertising')


def on_accept(client_address):
    """Called when a bluetooth client connects."""
    logging.info('Client connected: %r', client_address)


def on_disconnect(client_address):
    """Called when a bluetooth client disconnects."""
    logging.info('Client disconnected: %r', client_address)


def graceful_exit(bleno):
    """Graceful exit function, stop advertising and disconnect clients."""
    bleno.stopAdvertising()
    bleno.disconnect()
    logging.info('Stopping OpenTrickler Bluetooth...')


def all_variables_set(memcache, constants):
    """Validation function to assert that the expected trickler variables are set (not None) before operating."""
    variables = (
        memcache.get(constants.AUTO_MODE.value, None) is not None,
        memcache.get(constants.SCALE_STATUS.value, None) is not None,
        memcache.get(constants.SCALE_WEIGHT.value, None) is not None,
        memcache.get(constants.SCALE_UNIT.value, None) is not None,
        memcache.get(constants.TARGET_WEIGHT.value, None) is not None,
        memcache.get(constants.TARGET_UNIT.value, None) is not None,
    )
    logging.info('Variables: %r', variables)
    return all(variables)


def run(config, memcache, args):
    """Main Bluetooth control loop."""
    constants = enum.Enum('memcache_vars', config['memcache_vars'])

    logging.info('Setting up Bluetooth...')
    trickler_service = TricklerService(memcache, constants)
    device_name = config['bluetooth']['name']
    os.environ['BLENO_DEVICE_NAME'] = device_name
    logging.info('Bluetooth device will be advertised as %s', device_name)
    bleno = pybleno.Bleno()
    atexit.register(functools.partial(graceful_exit, bleno))

    # pylint: disable=no-member
    bleno.on('stateChange', functools.partial(on_state_change, device_name, bleno, trickler_service))
    bleno.on('advertisingStart', functools.partial(on_advertising_start, bleno, trickler_service))
    bleno.on('advertisingStop', on_advertising_stop)
    bleno.on('accept', on_accept)
    bleno.on('disconnect', on_disconnect)
    # pylint: enable=no-member

    logging.info('Checking if ready to advertise...')
    while 1:
        if all_variables_set(memcache, constants):
            logging.info('Ready to advertise!')
            break
        time.sleep(0.1)

    logging.info('Advertising OpenTrickler over Bluetooth...')
    bleno.start()

    logging.info('Starting OpenTrickler Bluetooth daemon...')
    # Loop and keep TricklerService property values up to date from memcache.
    while 1:
        try:
            trickler_service.all_mc_update()
        except (AttributeError, OSError):
            logging.exception('Caught possible bluetooth exception.')
        time.sleep(0.1)

    logging.info('Stopping bluetooth daemon...')


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

    # Run the main bluetooth control loop.
    run(config, memcache_client, args)
