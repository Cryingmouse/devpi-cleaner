=============
Devpi Cleaner
=============

Léon, the devpi cleaner, enables batch removal of artefacts from a `devpi server`_. Given a package and version
specification, it will remove the specified versions of a package from either a single index or all indices of a given
user.

Rationale
=========
Devpi cleaner wraps the original `devpi remove` command. It provides the following extensions:

* Conditionally limit removal to development packages.
* Conditionally limit removal to versions matching a given regular expression.
* Temporarily switch non-volatile indices to volatile.
* Apply a remove operation to all indices of a user.
* Throttle removal activities if the Devpi server is having difficulties keeping up.

Léon by Example
===============

The following command will delete all development packages preceding version 0.2 of ``delete_me`` on index `index1` of
the user::

    > devpi-cleaner http://localhost:2414/ user/index1 'delete_me<=0.2' --dev-only
    Packages to be deleted from user/index1:
     * delete_me 0.2.dev1 on user/index1
     * delete_me 0.2.dev2 on user/index1
    Cleaning user/index1…
    100% (2 of 2) |###########################| Elapsed Time: 0:00:00 Time: 0:00:00
    >

As shown, packages will be listed and confirmation required before they are actually deleted from the server.

Commandline Usage

=================

    Usage: devpi-cleaner [OPTIONS] SERVER user[/index] PACKAGE_SPECIFICATION

    Options:
      --keep-latest INTEGER   Number of latest versions to retain after applying
                              filters. Older versions beyond this count will be
                              removed.
      --batch                 Assume yes on confirmation questions.
      --dev-only              Remove only development versions as specified by PEP
                              440.
      --version-filter REGEX  Remove only versions in which the given regular
                              expression can be found.
      --force                 Temporarily make indices volatile to enable package
                              removal.
      --login TEXT            The user name to user for authentication. Defaults
                              to the user of the indices to operate on.
      --password TEXT         The password with which to authenticate.
      --help                  Show this message and exit.
