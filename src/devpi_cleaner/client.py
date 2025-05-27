# coding=utf-8
import re
import time
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional
from typing import Pattern
from typing import Set
from typing import Tuple

from devpi_plumber.client import volatile_index

_TAR_GZ_END = ".tar.gz"
_TAR_BZ2_END = ".tar.bz2"
_ZIP_END = ".zip"
_WHL_END = ".whl"
_EGG_END = ".egg"


def _extract_name_and_version(filename: str) -> Tuple[str, str]:
    path = Path(filename)
    if path.suffix == _WHL_END or path.suffix == _EGG_END:
        return tuple(path.stem.split("-")[:2])

    parts = filename.rsplit("-", 1)
    if len(parts) < 2 or not parts[1][0].isdigit():
        parts = filename.split("-")
        name = "-".join(parts[:-2])
        version_and_ext = "-".join(parts[-2:])
    else:
        name, version_and_ext = parts

    for extension in (_TAR_GZ_END, _TAR_BZ2_END, _ZIP_END):
        if version_and_ext.endswith(extension):
            return name, version_and_ext[: -len(extension)]

    raise NotImplementedError(f"Unknown package type. Cannot extract version from {filename}.")


class Package:
    def __init__(self, package_url: str):
        # example URL http://localhost:2414/user/index1/+f/45b/301745c6d8bbf/delete_me-0.1.tar.gz
        parts = package_url.rsplit("/", 6)
        self.index = f"{parts[1]}/{parts[2]}"
        self.name, self.version = _extract_name_and_version(parts[-1])

    def __str__(self) -> str:
        return f"{self.name} {self.version} on {self.index}"

    @property
    def is_dev_package(self) -> bool:
        return ".dev" in self.version

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Package):
            return False
        return self.index == other.index and self.name == other.name and self.version == other.version

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self.index, self.name, self.version))


def _list_packages_on_index(
    client, index: str, package_spec: str, only_dev: bool, version_filter: Optional[str]
) -> Set[Package]:
    version_filter_pattern: Optional[Pattern[str]] = re.compile(version_filter) if version_filter else None

    def selector(package: Package) -> bool:
        return (
            package.index == index
            and (not only_dev or package.is_dev_package)
            and (version_filter_pattern is None or version_filter_pattern.search(package.version))
        )

    client.use(index)

    all_packages = {
        Package(package_url)
        for package_url in client.list("--index", index, "--all", package_spec)
        if package_url.startswith(("http://", "https://"))
    }

    return set(filter(selector, all_packages))


def _get_indices(client, index_spec: str) -> List[str]:
    spec_parts = index_spec.split("/")
    return [index_spec] if len(spec_parts) > 1 else client.list_indices(user=index_spec)


def list_packages_by_index(
    client, index_spec: str, package_spec: str, only_dev: bool, version_filter: Optional[str]
) -> Dict[str, Set[Package]]:
    return {
        index: _list_packages_on_index(client, index, package_spec, only_dev, version_filter)
        for index in _get_indices(client, index_spec)
    }


def get_index_queue_size(metrics: List[Tuple[str, ...]]) -> int:
    for metric_name, _, value in metrics:
        if metric_name == "devpi_web_whoosh_index_queue_size":
            return value
    return 0


def wait_for_sync(client) -> None:
    """Wait for Devpi replicas to be in sync after deletion."""
    start = time.time()
    while time.time() < start + 1800:  # up to 30 minutes
        status = client.get_json("/+status")["result"]
        last_in_sync = float(status.get("replica-in-sync-at", time.time()))
        indexer_queue_size = get_index_queue_size(status.get("metrics", []))
        if last_in_sync > time.time() - 60 and indexer_queue_size < 100:
            # We are neither talking to a lagging replica nor is the instance
            # swamped with items to index. Should be fine to add some load.
            return
        # Wait for Devpi to catch up
        time.sleep(10)
    # At some point we just have to continue, maybe we are lucky and this goes through


def remove_package(client, package: Package) -> None:
    client.remove("--index", package.index, f"{package.name}=={package.version}")


def remove_packages(client, index: str, packages: List[Package], force: bool) -> None:
    with volatile_index(client, index, force):
        for package in packages:
            assert package.index == index
            wait_for_sync(client)
            remove_package(client, package)
