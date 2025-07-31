# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.setting import Setting  # noqa: E501
from openapi_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_get_settings(self):
        """Test case for get_settings

        Read Open Trickler settings
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/trickler/v1/settings',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_update_settings(self):
        """Test case for update_settings

        Update Open Trickler settings
        """
        setting = {"auto_mode":True,"target_unit":"g","target_weight":"target_weight"}
        headers = { 
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/trickler/v1/settings',
            method='PUT',
            headers=headers,
            data=json.dumps(setting),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
