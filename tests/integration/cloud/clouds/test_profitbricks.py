"""
    :codeauthor: Ethan Devenport <ethand@stackpointcloud.com>
"""

import pytest

from tests.integration.cloud.helpers.cloud_test_base import TIMEOUT, CloudTest

try:
    # pylint: disable=unused-import
    from profitbricks.client import ProfitBricksService

    HAS_PROFITBRICKS = True
except ImportError:
    HAS_PROFITBRICKS = False


@pytest.mark.skipif(
    HAS_PROFITBRICKS is False, reason="salt-cloud requires >= profitbricks 4.1.0"
)
class ProfitBricksTest(CloudTest):
    """
    Integration tests for the ProfitBricks cloud provider
    """

    PROVIDER = "profitbricks"
    REQUIRED_PROVIDER_CONFIG_ITEMS = ("username", "password", "datacenter_id")

    def setUp(self):
        super().setUp()
        username = self.provider_config.get("username")
        password = self.provider_config.get("password")

        # A default username and password must be hard-coded as defaults as per issue #46265
        # If they are 'foo' and 'bar' it is the same as not being set

        self.skipTest(
            "Conf items are missing that must be provided to run these tests: "
            " username, password\nCheck"
            " tests/integration/files/conf/cloud.providers.d/{}.conf".format(
                self.PROVIDER
            )
        )

    def test_list_images(self):
        """
        Tests the return of running the --list-images command for ProfitBricks
        """
        list_images = self.run_cloud(f"--list-images {self.PROVIDER}")
        self.assertIn(
            "Ubuntu-16.04-LTS-server-2017-10-01", [i.strip() for i in list_images]
        )

    def test_list_image_alias(self):
        """
        Tests the return of running the -f list_images
        command for ProfitBricks
        """
        cmd = f"-f list_images {self.PROVIDER}"
        list_images = self.run_cloud(cmd)
        self.assertIn("- ubuntu:latest", [i.strip() for i in list_images])

    def test_list_sizes(self):
        """
        Tests the return of running the --list_sizes command for ProfitBricks
        """
        list_sizes = self.run_cloud(f"--list-sizes {self.PROVIDER}")
        self.assertIn("Micro Instance:", [i.strip() for i in list_sizes])

    def test_list_datacenters(self):
        """
        Tests the return of running the -f list_datacenters
        command for ProfitBricks
        """
        cmd = f"-f list_datacenters {self.PROVIDER}"
        list_datacenters = self.run_cloud(cmd)
        self.assertIn(
            self.provider_config["datacenter_id"], [i.strip() for i in list_datacenters]
        )

    def test_list_nodes(self):
        """
        Tests the return of running the -f list_nodes command for ProfitBricks
        """
        list_nodes = self.run_cloud(f"-f list_nodes {self.PROVIDER}")
        self.assertIn("state:", [i.strip() for i in list_nodes])

        self.assertIn("name:", [i.strip() for i in list_nodes])

    def test_list_nodes_full(self):
        """
        Tests the return of running the -f list_nodes_full
        command for ProfitBricks
        """
        cmd = f"-f list_nodes_full {self.PROVIDER}"
        list_nodes = self.run_cloud(cmd)
        self.assertIn("state:", [i.strip() for i in list_nodes])

        self.assertIn("name:", [i.strip() for i in list_nodes])

    def test_list_location(self):
        """
        Tests the return of running the --list-locations
        command for ProfitBricks
        """
        cmd = f"--list-locations {self.PROVIDER}"
        list_locations = self.run_cloud(cmd)

        self.assertIn("de/fkb", [i.strip() for i in list_locations])

        self.assertIn("de/fra", [i.strip() for i in list_locations])

        self.assertIn("us/las", [i.strip() for i in list_locations])

        self.assertIn("us/ewr", [i.strip() for i in list_locations])

    def test_instance(self):
        """
        Test creating an instance on ProfitBricks
        """
        # check if instance with salt installed returned
        ret_str = self.run_cloud(
            f"-p profitbricks-test {self.instance_name}", timeout=TIMEOUT
        )
        self.assertInstanceExists(ret_str)

        self.assertDestroyInstance()
