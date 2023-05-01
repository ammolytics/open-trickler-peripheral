#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""

import atexit
import collections
import decimal
import enum
import logging
import time

import serial # pylint: disable=import-error;

import helpers


class ScaleException(Exception):
    pass


class ScaleNotReady(ScaleException):
    pass


def noop(*args, **kwargs):
    """No-op function for scales to use on throwaway status updates."""
    return


class SerialScale: # pylint: disable=too-many-instance-attributes;
    """Base class for a digital scale connected over a serial port."""

    class Units(enum.Enum):
        """Unit map as supported by the scale. Override this in subclasses when needed."""
        GRAINS = 0
        GRAMS = 1

    class StatusMap(enum.Enum):
        """Status value mapping, only reference those supported by your scale."""
        STABLE = 0
        UNSTABLE = 1
        OVERLOAD = 2
        ERROR = 3
        MODEL_NUMBER = 4
        SERIAL_NUMBER = 5
        ACKNOWLEDGE = 6

    def __init__(self, config, **kwargs):
        """Base scale class constructor. Should not usually need to be overridden."""
        # Store memcache client if provided.
        self._memcache = kwargs.get('memcache')
        # Pull default values from config, giving preference to provided arguments.
        self._constants = enum.Enum('memcache_vars', dict(config['memcache_vars']))

        # Set up crash protection that closes the serial port so the program can restart.
        atexit.register(self._graceful_exit)

        # Set up the internal serial port connection.
        port = kwargs.get('port', config['scale']['port'])
        baudrate = kwargs.get('baudrate', int(config['scale']['baudrate']))
        timeout = kwargs.get('timeout', float(config['scale']['timeout']))
        try:
            self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        except (serial.SerialException, FileNotFoundError):
            logging.exception('Scale is not ready! The error traceback follows for context.')
            raise ScaleNotReady()

        # Set default values, which should be overwritten quickly.
        self.unit = self.Units.GRAINS
        self.resolution = self.resolution_map[self.unit]
        self.weight = decimal.Decimal('0.00')
        self.status = self.StatusMap.STABLE
        self._store_scale_config()
        # Internal storage for scale readings to infer stability, used for scales that don't provide it.
        self._readings = collections.deque(maxlen=int(config['scale']['stable_reading_length']))

    def _update_memcache(self):
        """ Update memcache values if the memcache client has been provided."""
        if self._memcache:
            self._memcache.set_multi({
                self._constants.SCALE_STATUS.value: self.status,
                self._constants.SCALE_WEIGHT.value: self.weight,
                self._constants.SCALE_UNIT.value: self.unit,
                self._constants.SCALE_RESOLUTION.value: self.resolution,
                self._constants.SCALE_IS_STABLE.value: self.is_stable,
            })

    def _graceful_exit(self):
        """Graceful exit, closes serial port."""
        logging.debug('Closing serial port...')
        self._serial.close()

    def _store_scale_config(self):
        """Store the unit and status maps into memcache for reference elsewhere."""
        if self._memcache:
            self._memcache.set_multi({
                self._constants.SCALE_UNITS.value: {x.name: x.value for x in self.Units},
                self._constants.SCALE_UNIT_MAP.value: {k: self.unit_map[k].value for k in self.unit_map},
                self._constants.SCALE_REVERSE_UNIT_MAP.value: {k.value: self.reverse_unit_map[k] for k in self.reverse_unit_map},
                self._constants.SCALE_RESOLUTION_MAP.value: {k.value: self.resolution_map[k] for k in self.resolution_map},
                self._constants.SCALE_STATUS_MAP.value: {x.name: x.value for x in self.StatusMap},
            })

    def _check_stability(self):
        """Checks the internal list of readings and infer if the scale reading is stable."""
        if len(self._readings) == self._readings.maxlen and len(set(self._readings)) == 1:
            self.status = self.StatusMap.STABLE
        else:
            self.status = self.StatusMap.UNSTABLE

    @classmethod
    @property
    def unit_map(cls):
        """Mapping of self.unit keys to string units of weight as used by the scale."""
        raise NotImplementedError('')

    @classmethod
    @property
    def reverse_unit_map(cls):
        """Reverse mapping of self.unit_map."""
        cache_hit =  getattr(cls, '__cached_reverse_unit_map', None)
        if cache_hit:
            return cache_hit
        reversed_map = dict((v, k) for k, v in cls.unit_map.items()) # pylint: disable=no-member;
        cls.__cached_reverse_unit_map = reversed_map
        return cls.__cached_reverse_unit_map

    @classmethod
    @property
    def resolution_map(cls):
        """Map self.Units to matching resolutions with decimal.Decimal values."""
        raise NotImplementedError('')

    @property
    def is_stable(self):
        """Returns True if the scale is stable, otherwise False."""
        return self.status == self.StatusMap.STABLE

    def change_unit(self):
        """Changes the unit of weight on the scale."""
        raise NotImplementedError('The change_unit() method needs to be defined in a brand-specific scale class.')

    def update(self):
        """Read from the serial port and update an instance of this class with the most recent values."""
        raise NotImplementedError('The update() method needs to be defined in a brand-specific scale class.')


class ANDScale(SerialScale):
    """Class for controlling an A&D FX120 scale."""

    def __init__(self, config, port='/dev/ttyUSB0', baudrate=19200, timeout=0.1, **kwargs):
        """Only overriding this to provide scale specific constructor arguments."""
        super().__init__(config=config, port=port, baudrate=baudrate, timeout=timeout, **kwargs)

    @classmethod
    @property
    def unit_map(cls):
        """Mapping of self.unit keys to string units of weight as used by the scale."""
        return {
            'GN': cls.Units.GRAINS,
            'g': cls.Units.GRAMS,
        }

    @classmethod
    @property
    def resolution_map(cls):
        """Map self.units to matching resolutions with decimal.Decimal values."""
        return {
            cls.Units.GRAINS: decimal.Decimal('0.02'),
            cls.Units.GRAMS: decimal.Decimal('0.0001'),
        }

    def change_unit(self):
        """Changes the unit of weight on the scale."""
        logging.debug('changing weight unit on scale from: %r', self.unit)
        # Send Mode button command.
        self._serial.write(b'U\r\n')
        # Sleep 1s and wait for change to take effect.
        time.sleep(1)
        # Run update fn to set latest values.
        self.update()

    def update(self):
        """Read from the serial port and update an instance of this class with the most recent values."""
        # Status values (provided by the AND scales) mapped to functions to handle those cases.
        handlers = {
            'ST': self._stable,
            'US': self._unstable,
            'OL': self._overload,
            'EC': self._error,
            'AK': self._acknowledge,
            'TN': self._model_number,
            'SN': self._serial_number,
            None: noop,
        }

        # Note: The input buffer can fill up, causing latency. Clear it before reading.
        self._serial.reset_input_buffer()
        raw = self._serial.readline()
        logging.debug(raw)
        try:
            # Remove all leading and trailing whitespace characters then decode from bytestring into unicode.
            line = raw.strip().decode('utf-8')
        except UnicodeDecodeError:
            logging.debug('Could not decode bytes to unicode.')
        else:
            # Pull the first characters (status code, on this scale)
            prefix = line[0:2]
            # Get a handler function based on the prefix
            handler = handlers.get(prefix, noop)
            # Run the function to handle the input.
            handler(line)

    def _stable_unstable(self, line):
        """Update the scale when status is stable or unstable."""
        # Store the numeric weight from the scale reading.
        weight = line[3:12].strip()
        self.weight = decimal.Decimal(weight)
        # Get the unit of measurement from the scale reading and store the mapped value.
        unit = line[12:15].strip()
        self.unit = self.unit_map[unit]
        # Update the resolution according to the current unit of measure and supported resolutions.
        self.resolution = self.resolution_map[self.unit]
        # Update memcache values.
        self._update_memcache()

    def _stable(self, line):
        """Scale is stable."""
        self.status = self.StatusMap.STABLE
        self._stable_unstable(line)

    def _unstable(self, line):
        """Scale is unstable."""
        self.status = self.StatusMap.UNSTABLE
        self._stable_unstable(line)

    def _overload(self, line):
        """Scale is overloaded."""
        self.status = self.StatusMap.OVERLOAD
        self._update_memcache()

    def _error(self, line):
        """Scale has an error."""
        self.status = self.StatusMap.ERROR
        self._update_memcache()

    def _acknowledge(self, line):
        """Scale has acknowledged a command."""
        self.status = self.StatusMap.ACKNOWLEDGE
        self._update_memcache()

    def _model_number(self, line):
        """Gets & prints the scale's model number."""
        self.status = self.StatusMap.MODEL_NUMBER
        model_number = line[3:]
        logging.info('scale model number: %s', model_number)

    def _serial_number(self, line):
        """Gets & prints the scale's serial number."""
        self.status = self.StatusMap.SERIAL_NUMBER
        serial_number = line[3:]
        logging.info('scale serial number: %s', serial_number)


class CreedmoorScale(SerialScale):
    """Class for controlling a Creedmoor Sports TRX-925 scale."""

    def __init__(self, config, port='/dev/ttyUSB0', baudrate=9600, timeout=0.1, **kwargs):
        """Only overriding this to provide scale specific constructor arguments."""
        super().__init__(config=config, port=port, baudrate=baudrate, timeout=timeout, **kwargs)

    @classmethod
    @property
    def unit_map(cls):
        """Mapping of self.unit keys to string units of weight as used by the scale."""
        return {
            'GN': cls.Units.GRAINS,
            'g': cls.Units.GRAMS,
         }

    @classmethod
    @property
    def resolution_map(cls):
        """Map self.units to matching resolutions with decimal.Decimal values."""
        return {
            cls.Units.GRAINS: decimal.Decimal('0.01'),
            cls.Units.GRAMS: decimal.Decimal('0.0001'),
        }

    # Note(eric): There is no documentation on how to do this for this scale.
    def change_unit(self):
        """Changes the unit of weight on the scale."""
        logging.debug('changing weight unit on scale from: %r', self.unit)
        # Send Mode button command.
        self._serial.write(b'U\r\n')
        # Sleep 1s and wait for change to take effect.
        time.sleep(1)
        # Run update fn to set latest values.
        self.update()

    def update(self):
        """Read from the serial port and update an instance of this class with the most recent values."""
        handlers = {
            '+': self._stable_unstable,
            '-': self._stable_unstable,
            None: noop,
        }

        # Note: The input buffer can fill up, causing latency. Clear it before reading.
        self._serial.reset_input_buffer()
        raw = self._serial.readline()
        logging.debug(raw)
        try:
            # Remove trailing newline characters, then decode from bytestring into unicode.
            line = raw.rstrip(b'\r\n').decode('utf-8')
        except UnicodeDecodeError:
            logging.debug('Could not decode bytes to unicode.')
        else:
            # Pull the first character (positive or negative, on this scale)
            prefix = line[0:1]
            # Get a handler function based on the prefix
            handler = handlers.get(prefix, noop)
            # Run the function to handle the input.
            handler(line)

    def _stable_unstable(self, line):
        """Update the scale when status is stable or unstable."""
        # Push the latest reading into the internal list.
        self._readings.append(line)
        # Update internal stability bit.
        self._check_stability()
        # Store the numeric weight from the scale reading.
        weight = line[0:8]
        self.weight = decimal.Decimal(weight)
        # Get the unit of measurement from the scale reading and store the mapped value.
        unit = line[9:11]
        self.unit = self.unit_map[unit]
        # Update the resolution according to the current unit of measure and supported resolutions.
        self.resolution = self.resolution_map[self.unit]
        # Update memcache values.
        self._update_memcache()
        
        
class USSolidScale(SerialScale):
    """Class for controlling a U.S. Solid USS-DBS81-110G scale."""

    def __init__(self, config, port='/dev/ttyUSB0', baudrate=9600, timeout=0.1, **kwargs):
        """Only overriding this to provide scale specific constructor arguments."""
        super().__init__(config=config, port=port, baudrate=baudrate, timeout=timeout, **kwargs)

    @classmethod
    @property
    def unit_map(cls):
        """Mapping of self.unit keys to string units of weight as used by the scale."""
        return {
            'gn': cls.Units.GRAINS,
            'g': cls.Units.GRAMS,
         }

    @classmethod
    @property
    def resolution_map(cls):
        """Map self.units to matching resolutions with decimal.Decimal values."""
        return {
            cls.Units.GRAINS: decimal.Decimal('0.001'),
            cls.Units.GRAMS: decimal.Decimal('0.001'),
        }

    # Note(eric): There is no documentation on how to do this for this scale.
    def change_unit(self):
        """Changes the unit of weight on the scale."""
        logging.debug('changing weight unit on scale from: %r', self.unit)
        # Send Mode button command.
        self._serial.write(b'U\r\n')
        # Sleep 1s and wait for change to take effect.
        time.sleep(1)
        # Run update fn to set latest values.
        self.update()

    def update(self):
        """Read from the serial port and update an instance of this class with the most recent values."""
        handlers = {
            '+': self._stable_unstable,
            '-': self._stable_unstable,
            None: noop,
        }

        # Note: The input buffer can fill up, causing latency. Clear it before reading.
        self._serial.reset_input_buffer()
        raw = self._serial.readline()
        logging.debug(raw)
        try:
            # Remove trailing newline characters, then decode from bytestring into unicode.
            line = raw.rstrip(b'\r\n').decode('utf-8')
        except UnicodeDecodeError:
            logging.debug('Could not decode bytes to unicode.')
        else:
            # Pull the first character (positive or negative, on this scale)
            prefix = line[0:1]
            # Get a handler function based on the prefix
            handler = handlers.get(prefix, noop)
            # Run the function to handle the input.
            handler(line)

    def _stable_unstable(self, line):
        """Update the scale when status is stable or unstable."""
        # Push the latest reading into the internal list.
        self._readings.append(line)
        # Update internal stability bit.
        self._check_stability()
        # Store the numeric weight from the scale reading.
        weight = line[0:9]
        weight = weight.replace(' ', '')
        self.weight = decimal.Decimal(weight)
        # Get the unit of measurement from the scale reading and store the mapped value.
        unit = line[9:11].strip()
        self.unit = self.unit_map[unit]
        # Update the resolution according to the current unit of measure and supported resolutions.
        self.resolution = self.resolution_map[self.unit]
        # Update memcache values.
        self._update_memcache()


SCALES = {
    'and': ANDScale,
    'creedmoor': CreedmoorScale,
    'ussolid' : USSolidScale,
    # Legacy naming support.
    'and-fx120': ANDScale,
}


# Handle command-line execution.
if __name__ == '__main__':
    import argparse
    import configparser


    # Default argument values.
    DEFAULTS = dict(
        verbose = False,
        scale = 'and-fx120',
        scale_port = '/dev/ttyUSB0',
        scale_baudrate = 19200,
        scale_timeout = 0.1,
    )

    parser = argparse.ArgumentParser(description='Test scale.')
    parser.add_argument('config_file')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--scale', choices=SCALES.keys())
    parser.add_argument('--scale_port')
    parser.add_argument('--scale_baudrate', type=int)
    parser.add_argument('--scale_timeout', type=float)
    args = parser.parse_args()

    # Parse the config file.
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(args.config_file)

    # Order of priority is 1) command-line argument, 2) config file, 3) default.
    kwargs = {}
    VERBOSE = DEFAULTS['verbose'] or config['general']['verbose']
    SCALE_MODEL = DEFAULTS['scale'] or config['scale']['model']
    SCALE_PORT = DEFAULTS['scale_port'] or config['scale']['port']
    SCALE_BAUDRATE = DEFAULTS['scale_baudrate'] or config['scale']['baudrate']
    SCALE_TIMEOUT = DEFAULTS['scale_timeout'] or config['scale']['timeout']
    if args.verbose is not None:
        VERBOSE = args.verbose
        kwargs['verbose'] = args.verbose
    if args.scale is not None:
        SCALE_MODEL = args.scale
        kwargs['scale_model'] = args.scale
    if args.scale_port is not None:
        kwargs['port'] = args.scale_port
    if args.scale_baudrate is not None:
        kwargs['baudrate'] = args.scale_baudrate
    if args.scale_timeout is not None:
        kwargs['timeout'] = args.scale_timeout

    # Configure Python logging.
    LOG_LEVEL = logging.INFO
    if VERBOSE:
        LOG_LEVEL = logging.DEBUG
    helpers.setup_logging(LOG_LEVEL)

    # Setup memcache.
    memcache_client = helpers.get_mc_client()

    # Create a Scale instance and run .update() in a loop, which should print the values.
    scale_cls = SCALES[SCALE_MODEL]
    scale = scale_cls(
        config=config,
        memcache=memcache_client,
        **kwargs)

    while 1:
        scale.update()
