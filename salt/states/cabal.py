"""
Installation of Cabal Packages
==============================

.. versionadded:: 2015.8.0

These states manage the installed packages for Haskell using
cabal. Note that cabal-install must be installed for these states to
be available, so cabal states should include a requisite to a
pkg.installed state for the package which provides cabal
(``cabal-install`` in case of Debian based distributions). Example::

.. code-block:: yaml

   cabal-install:
     pkg.installed

   ShellCheck:
     cabal.installed:
       - require:
         - pkg: cabal-install

"""

import salt.utils.path
from salt.exceptions import CommandExecutionError, CommandNotFoundError


def __virtual__():
    """
    Only work when cabal-install is installed.
    """
    if (salt.utils.path.which("cabal") is not None) and (
        salt.utils.path.which("ghc-pkg") is not None
    ):
        return True
    return (False, "cabal or ghc-pkg commands not found")


def _parse_pkg_string(pkg):
    """
    Parse pkg string and return a tuple of package name, separator, and
    package version.

    Cabal support install package with following format:

    * foo-1.0
    * foo < 1.2
    * foo > 1.3

    For the sake of simplicity only the first form is supported,
    support for other forms can be added later.
    """
    pkg_name, separator, pkg_ver = pkg.partition("-")
    return (pkg_name.strip(), separator, pkg_ver.strip())


def installed(name, pkgs=None, user=None, install_global=False, env=None):
    """
    Verify that the given package is installed and is at the correct version
    (if specified).

    .. code-block:: yaml

        ShellCheck-0.3.5:
          cabal:
            - installed:

    name
        The package to install
    user
        The user to run cabal install with
    install_global
        Install package globally instead of locally
    env
        A list of environment variables to be set prior to execution. The
        format is the same as the :py:func:`cmd.run <salt.states.cmd.run>`.
        state function.
    """
    ret = {"name": name, "result": None, "comment": "", "changes": {}}

    try:
        call = __salt__["cabal.update"](user=user, env=env)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret["result"] = False
        ret["comment"] = f"Could not run cabal update {err}"
        return ret

    if pkgs is not None:
        pkg_list = pkgs
    else:
        pkg_list = [name]

    try:
        installed_pkgs = __salt__["cabal.list"](user=user, installed=True, env=env)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret["result"] = False
        ret["comment"] = f"Error looking up '{name}': {err}"
        return ret

    pkgs_satisfied = []
    pkgs_to_install = []

    for pkg in pkg_list:
        pkg_name, _, pkg_ver = _parse_pkg_string(pkg)

        if pkg_name not in installed_pkgs:
            pkgs_to_install.append(pkg)
        else:
            if pkg_ver:  # version is specified
                if installed_pkgs[pkg_name] != pkg_ver:
                    pkgs_to_install.append(pkg)
                else:
                    pkgs_satisfied.append(pkg)
            else:
                pkgs_satisfied.append(pkg)

    if __opts__["test"]:
        ret["result"] = None

        comment_msg = []

        if pkgs_to_install:
            comment_msg.append(
                "Packages(s) '{}' are set to be installed".format(
                    ", ".join(pkgs_to_install)
                )
            )

        if pkgs_satisfied:
            comment_msg.append(
                "Packages(s) '{}' satisfied by {}".format(
                    ", ".join(pkg_list), ", ".join(pkgs_satisfied)
                )
            )

        ret["comment"] = ". ".join(comment_msg)
        return ret

    if not pkgs_to_install:
        ret["result"] = True
        ret["comment"] = "Packages(s) '{}' satisfied by {}".format(
            ", ".join(pkg_list), ", ".join(pkgs_satisfied)
        )

        return ret

    try:
        call = __salt__["cabal.install"](
            pkgs=pkg_list, user=user, install_global=install_global, env=env
        )
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret["result"] = False
        ret["comment"] = "Error installing '{}': {}".format(", ".join(pkg_list), err)
        return ret

    if call and isinstance(call, dict):
        ret["result"] = True
        ret["changes"] = {"old": [], "new": pkgs_to_install}
        ret["comment"] = "Packages(s) '{}' successfully installed".format(
            ", ".join(pkgs_to_install)
        )
    else:
        ret["result"] = False
        ret["comment"] = "Could not install packages(s) '{}'".format(
            ", ".join(pkg_list)
        )

    return ret


def removed(name, user=None, env=None):
    """
    Verify that given package is not installed.
    """

    ret = {"name": name, "result": None, "comment": "", "changes": {}}

    try:
        installed_pkgs = __salt__["cabal.list"](user=user, installed=True, env=env)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret["result"] = False
        ret["comment"] = f"Error looking up '{name}': {err}"

    if name not in installed_pkgs:
        ret["result"] = True
        ret["comment"] = f"Package '{name}' is not installed"
        return ret

    if __opts__["test"]:
        ret["result"] = None
        ret["comment"] = f"Package '{name}' is set to be removed"
        return ret

    if __salt__["cabal.uninstall"](pkg=name, user=user, env=env):
        ret["result"] = True
        ret["changes"][name] = "Removed"
        ret["comment"] = f"Package '{name}' was successfully removed"
    else:
        ret["result"] = False
        ret["comment"] = f"Error removing package '{name}'"

    return ret
