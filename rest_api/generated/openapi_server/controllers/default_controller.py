import connexion
import enum
import six
from typing import Dict
from typing import Tuple
from typing import Union

import pymemcache.client.base # pylint: disable=import-error;
import pymemcache.serde # pylint: disable=import-error;

from openapi_server.models.setting import Setting  # noqa: E501
from openapi_server import util


def get_mc_client(server='127.0.0.1:11211'):
    return pymemcache.client.base.Client(
        server,
        serde=pymemcache.serde.PickleSerde(),
        connect_timeout=10,
        timeout=2)


MC_CLIENT = get_mc_client()
AUTO_MODE = 'auto_mode'
TARGET_UNIT = 'target_unit'
TARGET_WEIGHT = 'target_weight'


class Units(enum.Enum):
    GRAINS = 0
    GRAMS = 1


UNIT_MAP = {
    'GN': Units.GRAINS,
    'g': Units.GRAMS,
}


def get_settings():  # noqa: E501
    """Read Open Trickler settings

     # noqa: E501


    :rtype: Union[Setting, Tuple[Setting, int], Tuple[Setting, int, Dict[str, str]]
    """
    return {
        'auto_mode': MC_CLIENT.get(AUTO_MODE),
        'target_unit': MC_CLIENT.get(TARGET_UNIT),
        'target_weight': MC_CLIENT.get(TARGET_WEIGHT),
    }


def update_settings(setting):  # noqa: E501
    """Update Open Trickler settings

     # noqa: E501

    :param setting: New setting values
    :type setting: dict | bytes

    :rtype: Union[None, Tuple[None, int], Tuple[None, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        setting = Setting.from_dict(connexion.request.get_json())  # noqa: E501

    memcache.set(AUTO_MODE, setting.auto_mode or MC_CLIENT.get(AUTO_MODE))
    memcache.set(TARGET_WEIGHT, setting.target_weight or MC_CLIENT.get(TARGET_WEIGHT))
    memcache.set(TARGET_UNIT, UNIT_MAP.get(setting.target_unit, MC_CLIENT.get(TARGET_UNIT)))

    return {
        'auto_mode': MC_CLIENT.get('auto_mode'),
        'target_unit': MC_CLIENT.get('target_unit'),
        'target_weight': MC_CLIENT.get('target_weight'),
    }
