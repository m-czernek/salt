"""
    :codeauthor: :email:`Amel Ajdinovic <amel@stackpointcloud.com>`
"""

import pytest

from tests.integration.cloud.helpers.cloud_test_base import TIMEOUT, CloudTest

pytest.importorskip("oneandone.client", reason="salt-cloud requires >= 1and1 1.2.0")


class OneAndOneTest(CloudTest):
    """
    Integration tests for the 1and1 cloud provider
    """

    PROVIDER = "oneandone"
    REQUIRED_PROVIDER_CONFIG_ITEMS = ("api_token",)

    def test_list_images(self):
        """
        Tests the return of running the --list-images command for 1and1
        """
        image_list = self.run_cloud(f"--list-images {self.PROVIDER_NAME}")
        self.assertIn("coreOSimage", [i.strip() for i in image_list])

    def test_instance(self):
        """
        Test creating an instance on 1and1
        """
        # check if instance with salt installed returned
        ret_str = self.run_cloud(
            f"-p oneandone-test {self.instance_name}", timeout=TIMEOUT
        )
        self.assertInstanceExists(ret_str)

        self.assertDestroyInstance()
