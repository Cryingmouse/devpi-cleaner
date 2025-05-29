# coding=utf-8

import unittest
from unittest.mock import Mock
from unittest.mock import call

from ddt import data
from ddt import ddt
from ddt import unpack
from devpi_plumber.client import DevpiCommandWrapper

from devpi_cleaner.client import Package
from devpi_cleaner.client import list_packages_by_index
from devpi_cleaner.client import remove_packages


@ddt
class TestPackage(unittest.TestCase):
    @data(
        # Basic sdist
        (
            "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz",
            "user/index1",
            "delete_me",
            "0.1",
            False,
        ),
        # Zip format
        (
            "http://localhost:2414/user/index1/+f/45b/301745c6d8bbe/delete_me-0.1.zip",
            "user/index1",
            "delete_me",
            "0.1",
            False,
        ),
        # Name with dashes
        (
            "http://localhost:2414/user/index1/+f/45b/301745c6d7bbf/with-dashes-0.1.tar.gz",
            "user/index1",
            "with-dashes",
            "0.1",
            False,
        ),
        # Setuptools-scm version
        (
            "http://localhost:2414/user/index1/+f/25d/bb41cc64d762f/old_setuptools_used-2.1.2.dev7-ng8964316.tar.gz",
            "user/index1",
            "old_setuptools_used",
            "2.1.2.dev7-ng8964316",
            True,
        ),
        # Pyscaffold version
        (
            "http://localhost:2414/user/index1/+f/088/58034d63c6a98/old-setuptools-used-0.1.0.post0.dev4-g5e41942.tar.gz",
            "user/index1",
            "old-setuptools-used",
            "0.1.0.post0.dev4-g5e41942",
            True,
        ),
        # Wheel format
        (
            "http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl",
            "user/index1",
            "delete_me",
            "0.2.dev2",
            True,
        ),
        # Old setuptools wheel
        (
            "http://localhost:2414/user/index1/+f/475/732413fe3d8f8/old_setuptools_used-0.6b3.post0.dev27_gf3ac2d5-py2-none-any.whl",
            "user/index1",
            "old_setuptools_used",
            "0.6b3.post0.dev27_gf3ac2d5",
            True,
        ),
        # Egg format
        (
            "http://localhost:2414/user/index1/+f/636/95eef6acadc76/some_egg-0.1.dev4-py2.7.egg",
            "user/index1",
            "some_egg",
            "0.1.dev4",
            True,
        ),
        # HTTPS URL
        (
            "https://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl",
            "user/index1",
            "delete_me",
            "0.2.dev2",
            True,
        ),
        # Edge case: Version with build metadata
        (
            "https://localhost:2414/user/index2/+f/123/abc123def4567/my_pkg-1.0.0+20240515.tar.gz",
            "user/index2",
            "my_pkg",
            "1.0.0+20240515",
            False,
        ),
        # Edge case: Name with underscores and numbers
        (
            "https://localhost:2414/user/index3/+f/789/xyz987qwe654/py3_only_pkg-3.11.dev5-py3-none-any.whl",
            "user/index3",
            "py3_only_pkg",
            "3.11.dev5",
            True,
        ),
        # Edge case: Tar.bz2 extension
        (
            "http://localhost:2414/user/index4/+f/456/def456ghi789/legacy_app-2.3.4.tar.bz2",
            "user/index4",
            "legacy_app",
            "2.3.4",
            False,
        ),
        # Edge case: Very long version string
        (
            "http://localhost:2414/user/index5/+f/111/aaa111bbb222/very_long_name-1.2.3.4.5.6.7.8.9.10.dev1234567890.tar.gz",
            "user/index5",
            "very_long_name",
            "1.2.3.4.5.6.7.8.9.10.dev1234567890",
            True,
        ),
        # Edge case: Single character package name
        ("http://localhost:2414/user/index6/+f/999/zzz999yyy888/x-1.0.0.whl", "user/index6", "x", "1.0.0", False),
    )
    @unpack
    def test_package_properties(
        self, url: str, exp_index: str, exp_name: str, exp_version: str, exp_is_dev_package: bool
    ):
        package = Package(url)
        self.assertEqual(exp_index, package.index)
        self.assertEqual(exp_name, package.name)
        self.assertEqual(exp_version, package.version)
        self.assertEqual(exp_is_dev_package, package.is_dev_package)

    @data(
        ("http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz", "delete_me 0.1 on user/index1"),
        (
            "https://localhost:2414/user/index3/+f/789/xyz987qwe654/py3_only_pkg-3.11.dev5-py3-none-any.whl",
            "py3_only_pkg 3.11.dev5 on user/index3",
        ),
        (
            "http://localhost:2414/user/index4/+f/456/def456ghi789/legacy_app-2.3.4.tar.bz2",
            "legacy_app 2.3.4 on user/index4",
        ),
    )
    @unpack
    def test_string_representation(self, url: str, exp_str: str):
        package = Package(url)
        self.assertEqual(exp_str, str(package))

    def test_unknown_format(self):
        # Add more invalid extension cases
        invalid_urls = [
            "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.unkown",
            "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.rpm",
            "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.deb",
        ]
        for url in invalid_urls:
            with self.assertRaises(NotImplementedError):
                Package(url)


@ddt
class ListTests(unittest.TestCase):
    @data(
        (
            "user",
            "dummy",
            False,
            None,
            "http://dummy-server/user",
            ["user/eins", "user/zwei"],
            [
                ["http://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz"],
                ["http://dummy-server/user/zwei/+f/70e/3bc67b3194144/dummy-2.0.tar.gz"],
            ],
            {
                "user/eins": {Package("http://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz")},
                "user/zwei": {Package("http://dummy-server/user/zwei/+f/70e/3bc67b3194144/dummy-2.0.tar.gz")},
            },
        ),
        (
            "user/eins",
            "dummy",
            False,
            None,
            "http://dummy-server/user",
            ["user/eins", "user/zwei"],
            [["http://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz"]],
            {"user/eins": {Package("http://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz")}},
        ),
        (
            "user",
            "delete_me",
            False,
            None,
            "http://localhost:2414/user/index2",
            ["user/index2"],
            [
                [
                    "*redirected: http://localhost:2414/user/index2/delete_me",
                    "http://localhost:2414/user/index2/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index2/+f/313/8642d2b43a764/delete_me-0.2.tar.gz",
                    "http://localhost:2414/other_user/index1/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl",
                    "http://localhost:2414/other_user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz",
                ]
            ],
            {
                "user/index2": {
                    Package("http://localhost:2414/user/index2/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl")
                }
            },
        ),
        (
            "user",
            "delete_me",
            True,
            None,
            "http://localhost:2414/user/index1",
            ["user/index1"],
            [
                [
                    "http://localhost:2414/user/index1/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz",
                    "http://localhost:2414/user/index1/+f/bab/f9b37c9d0d192/delete_me-0.2a1.tar.gz",
                    "http://localhost:2414/user/index1/+f/e8e/d9cfe14d2ef65/delete_me-0.2a1-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/842/84d1283874110/delete_me-0.2.dev2.tar.gz",
                    "http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/c22/cdec16d5ddc3a/delete_me-0.1-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz",
                ]
            ],
            {
                "user/index1": {
                    Package(
                        "http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl"
                    )
                }
            },
        ),
        (
            "user",
            "delete_me",
            False,
            r"a\d+",
            "http://localhost:2414/user/index1",
            ["user/index1"],
            [
                [
                    "http://localhost:2414/user/index1/+f/70e/3bc67b3194143/delete_me-0.2-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz",
                    "http://localhost:2414/user/index1/+f/bab/f9b37c9d0d192/delete_me-0.2a1.tar.gz",
                    "http://localhost:2414/user/index1/+f/e8e/d9cfe14d2ef65/delete_me-0.2a1-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/842/84d1283874110/delete_me-0.2.dev2.tar.gz",
                    "http://localhost:2414/user/index1/+f/636/95eef6ac86c76/delete_me-0.2.dev2-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/c22/cdec16d5ddc3a/delete_me-0.1-py2.py3-none-any.whl",
                    "http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz",
                ]
            ],
            {"user/index1": {Package("http://localhost:2414/user/index1/+f/bab/f9b37c9d0d192/delete_me-0.2a1.tar.gz")}},
        )(
            "user",
            "dummy",
            False,
            None,
            "https://dummy-server/user",
            ["user/eins", "user/zwei"],
            [
                ["https://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz"],
                ["https://dummy-server/user/zwei/+f/70e/3bc67b3194144/dummy-2.0.tar.gz"],
            ],
            {
                "user/eins": {Package("https://dummy-server/user/eins/+f/70e/3bc67b3194143/dummy-1.0.tar.gz")},
                "user/zwei": {Package("https://dummy-server/user/zwei/+f/70e/3bc67b3194144/dummy-2.0.tar.gz")},
            },
        ),
    )
    @unpack
    def test_list_packages(
        self,
        index_arg: str,
        package_name: str,
        only_dev: bool,
        version_filter: str,
        base_url: str,
        indices: list,
        list_responses: list,
        expected_packages: dict,
    ):
        # Extract user from index_arg (user or user/index)
        user = index_arg.split("/")[0]

        # Create mock devpi_client
        devpi_client = Mock()
        devpi_client.user = user
        devpi_client.url = base_url
        devpi_client.list_indices.return_value = indices
        devpi_client.list.side_effect = list_responses

        # Call the function
        actual_packages = list_packages_by_index(devpi_client, index_arg, package_name, only_dev, version_filter)

        # Verify the result
        self.assertDictEqual(expected_packages, actual_packages)

        # Verify calls to devpi list command
        expected_calls = []
        if "/" in index_arg:
            # Single index call
            expected_calls.append(call("--index", index_arg, "--all", package_name))
        else:
            # Multiple indices calls
            for index in indices:
                expected_calls.append(call("--index", index, "--all", package_name))

        devpi_client.list.assert_has_calls(expected_calls, any_order=False)


class RemovalTests(unittest.TestCase):
    def test_remove(self):
        packages = [
            Package("http://localhost:2414/user/index1/+f/313/8642d2b43a764/delete_me-0.2.tar.gz"),
            Package("http://localhost:2414/user/index1/+f/313/8642d2b43a764/delete_me-0.3.tar.gz"),
        ]

        devpi_client = Mock(spec=DevpiCommandWrapper)
        devpi_client.modify_index.return_value = "volatile=True"
        devpi_client.get_json.return_value = {"result": {}}
        remove_packages(devpi_client, "user/index1", packages, False)

        self.assertEqual(2, devpi_client.remove.call_count)

    def test_aborts_if_package_on_wrong_index(self):
        packages = [Package("http://localhost:2414/user/index2/+f/313/8642d2b43a764/delete_me-0.2.tar.gz")]

        devpi_client = Mock(spec=DevpiCommandWrapper)
        devpi_client.modify_index.return_value = "volatile=True"

        with self.assertRaises(AssertionError):
            remove_packages(devpi_client, "user/index1", packages, False)

        self.assertLess(devpi_client.remove.call_count, 1)
