import connexion
import six
from typing import Dict
from typing import Tuple
from typing import Union

from openapi_server.models.setting import Setting  # noqa: E501
from openapi_server import util


def get_settings():  # noqa: E501
    """Read Open Trickler settings

     # noqa: E501


    :rtype: Union[Setting, Tuple[Setting, int], Tuple[Setting, int, Dict[str, str]]
    """
    return 'do some magic!'


def update_settings(setting):  # noqa: E501
    """Update Open Trickler settings

     # noqa: E501

    :param setting: New setting values
    :type setting: dict | bytes

    :rtype: Union[None, Tuple[None, int], Tuple[None, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        setting = Setting.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'
