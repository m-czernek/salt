"""
Module for managaging metadata in SmartOS Zones

.. versionadded:: 2016.3.0

:maintainer:    Jorge Schrauwen <sjorge@blackdot.be>
:maturity:      new
:platform:      smartos
"""

import logging

import salt.utils.decorators as decorators
import salt.utils.path
import salt.utils.platform

log = logging.getLogger(__name__)

# Function aliases
__func_alias__ = {
    "list_": "list",
    "get_": "get",
    "put_": "put",
    "delete_": "delete",
}

# Define the module's virtual name
__virtualname__ = "mdata"


@decorators.memoize
def _check_mdata_list():
    """
    looks to see if mdata-list is present on the system
    """
    return salt.utils.path.which("mdata-list")


@decorators.memoize
def _check_mdata_get():
    """
    looks to see if mdata-get is present on the system
    """
    return salt.utils.path.which("mdata-get")


@decorators.memoize
def _check_mdata_put():
    """
    looks to see if mdata-put is present on the system
    """
    return salt.utils.path.which("mdata-put")


@decorators.memoize
def _check_mdata_delete():
    """
    looks to see if mdata-delete is present on the system
    """
    return salt.utils.path.which("mdata-delete")


def __virtual__():
    """
    Provides mdata only on SmartOS
    """
    if _check_mdata_list() and not salt.utils.platform.is_smartos_globalzone():
        return __virtualname__
    return (
        False,
        f"{__virtualname__} module can only be loaded on SmartOS zones",
    )


def list_():
    """
    List available metadata

    CLI Example:

    .. code-block:: bash

        salt '*' mdata.list
    """
    mdata = _check_mdata_list()
    if mdata:
        cmd = f"{mdata}"
        return __salt__["cmd.run"](cmd, ignore_retcode=True).splitlines()
    return {}


def get_(*keyname):
    """
    Get metadata

    keyname : string
        name of key

    .. note::

        If no keynames are specified, we get all (public) properties

    CLI Example:

    .. code-block:: bash

        salt '*' mdata.get salt:role
        salt '*' mdata.get user-script salt:role
    """
    mdata = _check_mdata_get()
    ret = {}

    if not keyname:
        keyname = list_()

    for k in keyname:
        if mdata:
            cmd = f"{mdata} {k}"
            res = __salt__["cmd.run_all"](cmd, ignore_retcode=True)
            ret[k] = res["stdout"] if res["retcode"] == 0 else ""
        else:
            ret[k] = ""

    return ret


def put_(keyname, val):
    """
    Put metadata

    prop : string
        name of property
    val : string
        value to set

    CLI Example:

    .. code-block:: bash

        salt '*' mdata.list
    """
    mdata = _check_mdata_put()
    ret = {}

    if mdata:
        cmd = f"echo {val} | {mdata} {keyname}"
        ret = __salt__["cmd.run_all"](cmd, python_shell=True, ignore_retcode=True)

    return ret["retcode"] == 0


def delete_(*keyname):
    """
    Delete metadata

    prop : string
        name of property

    CLI Example:

    .. code-block:: bash

        salt '*' mdata.get salt:role
        salt '*' mdata.get user-script salt:role
    """
    mdata = _check_mdata_delete()
    valid_keynames = list_()
    ret = {}

    for k in keyname:
        if mdata and k in valid_keynames:
            cmd = f"{mdata} {k}"
            ret[k] = __salt__["cmd.run_all"](cmd, ignore_retcode=True)["retcode"] == 0
        else:
            ret[k] = True

    return ret
