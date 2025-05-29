import getpass
import re
import sys
from typing import Dict
from typing import Optional
from typing import Pattern
from typing import Set

import click
from devpi_plumber.client import DevpiClient
from devpi_plumber.client import DevpiClientError
from tqdm import tqdm

from devpi_cleaner.client import Package
from devpi_cleaner.client import list_packages_by_index
from devpi_cleaner.client import remove_package


@click.command()
@click.argument("server")
@click.argument("index_spec", metavar="user[/index]")
@click.argument("package_specification")
@click.option(
    "--keep-latest",
    help="Number of latest versions to retain after applying filters. Older versions beyond this count will be removed.",
    default=3,
)
@click.option("--batch", is_flag=True, help="Assume yes on confirmation questions.")
@click.option("--dev-only", is_flag=True, help="Remove only development versions as specified by PEP 440.")
@click.option(
    "--version-filter", metavar="REGEX", help="Remove only versions in which the given regular expression can be found."
)
@click.option("--force", is_flag=True, help="Temporarily make indices volatile to enable package removal.")
@click.option(
    "--login", help="The user name to user for authentication. Defaults to the user of the indices to operate on."
)
@click.option("--password", help="The password with which to authenticate.")
def clean_devpi_packages(
    server: str,
    index_spec: str,
    package_specification: str,
    keep_latest: Optional[int],
    batch: bool,
    dev_only: bool,
    version_filter: Optional[str],
    force: bool,
    password: Optional[str],
    login: Optional[str],
) -> None:
    login_user: str = login if login else index_spec.split("/")[0]
    if password is None:
        password = getpass.getpass()

    try:
        with DevpiClient(server, login_user, password) as client:
            version_filter_pattern: Optional[Pattern[str]] = re.compile(version_filter) if version_filter else None
            packages_by_index: Dict[str, Set[Package]] = list_packages_by_index(
                client=client,
                index_spec=index_spec,
                package_spec=package_specification,
                only_dev=dev_only,
                version_filter=version_filter_pattern,
                keep_latest=keep_latest,
            )

            for index, packages in packages_by_index.items():
                click.echo(f"Packages to be deleted from {index}: ")
                for package in packages:
                    click.echo(f" * {package}")

            if not batch:
                confirmation: str = click.prompt('Enter "yes" to confirm', type=str)
                if confirmation != "yes":
                    click.echo("Aborting...")
                    return

            for index, packages in packages_by_index.items():
                click.echo(f"Cleaning {index}…")
                # Explicitly marks package iterator with progress bar
                for package in tqdm(list(packages), desc=f"Progress: {index}", unit="package", leave=True):
                    remove_package(client, index, package, force)
    except DevpiClientError as client_error:
        click.echo(client_error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    clean_devpi_packages()
