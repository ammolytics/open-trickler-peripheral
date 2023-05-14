#!/usr/bin/env python3
"""
Copyright (c) Ammolytics and contributors. All rights reserved.
Released under the MIT license. See LICENSE file in the project root for details.

OpenTrickler
https://github.com/ammolytics/projects/tree/develop/trickler
"""
import array
import decimal
import logging
import struct

import pymemcache.client.base # pylint: disable=import-error;
import pymemcache.serde # pylint: disable=import-error;


def get_mc_client(server='127.0.0.1:11211'):
    """Returns a memcache client instance."""
    return pymemcache.client.base.Client(
        server,
        serde=pymemcache.serde.PickleSerde(),
        connect_timeout=10,
        timeout=2)


def setup_logging(level=logging.DEBUG):
    """Returns a configured logger instance."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s.%(msecs)06dZ %(levelname)-4s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S')


def is_even(dec):
    """Returns True if a decimal.Decimal is even, False if odd."""
    exp = dec.as_tuple().exponent
    factor = 10 ** (exp * -1)
    return (dec * factor) % 2 == 0


def noop(*args, **kwargs):
    """Simple noop function."""
    return None


def bool_to_bytes(value):
    """Converts bool to bytes."""
    data_bytes = array.array('B', [0] * 1)
    struct.pack_into("<B", data_bytes, 0, value)
    return data_bytes


def bytes_to_bool(data_bytes):
    """Converts bytes to boolean."""
    value = data_bytes[0]
    return bool(value)


def str_to_bytes(value):
    """Converts str to bytes."""
    data_bytes = array.array('B', [])
    data_bytes.frombytes(value.encode('utf-8'))
    return data_bytes


def bytes_to_str(data_bytes):
    """Converts bytes to str."""
    return data_bytes.decode('utf-8')


def decimal_to_bytes(value):
    """Converts decimal to bytes."""
    value = str(value)
    return str_to_bytes(value)


def bytes_to_decimal(data_bytes):
    """Converts bytes to decimal."""
    value = bytes_to_str(data_bytes)
    return decimal.Decimal(value)


def enum_to_bytes(value_enum):
    """Converts enum to bytes."""
    data_bytes = array.array('B', [0] * 1)
    struct.pack_into("<B", data_bytes, 0, value_enum.value)
    return data_bytes


def bytes_to_enum(enum_cls, data_bytes):
    """Converts bytes to enum."""
    value = data_bytes[0]
    return enum_cls(value)
