r"""
A salt util for modifying firewall settings.

.. versionadded:: 2018.3.4
.. versionadded:: 2019.2.0

This util allows you to modify firewall settings in the local group policy in
addition to the normal firewall settings. Parameters are taken from the
netsh advfirewall prompt.

.. note::
    More information can be found in the advfirewall context in netsh. This can
    be access by opening a netsh prompt. At a command prompt type the following:

    c:\>netsh
    netsh>advfirewall
    netsh advfirewall>set help
    netsh advfirewall>set domain help

Usage:

.. code-block:: python

    import salt.utils.win_lgpo_netsh

    # Get the inbound/outbound firewall settings for connections on the
    # local domain profile
    salt.utils.win_lgpo_netsh.get_settings(profile='domain',
                                           section='firewallpolicy')

    # Get the inbound/outbound firewall settings for connections on the
    # domain profile as defined by local group policy
    salt.utils.win_lgpo_netsh.get_settings(profile='domain',
                                           section='firewallpolicy',
                                           store='lgpo')

    # Get all firewall settings for connections on the domain profile
    salt.utils.win_lgpo_netsh.get_all_settings(profile='domain')

    # Get all firewall settings for connections on the domain profile as
    # defined by local group policy
    salt.utils.win_lgpo_netsh.get_all_settings(profile='domain', store='lgpo')

    # Get all firewall settings for all profiles
    salt.utils.win_lgpo_netsh.get_all_settings()

    # Get all firewall settings for all profiles as defined by local group
    # policy
    salt.utils.win_lgpo_netsh.get_all_settings(store='lgpo')

    # Set the inbound setting for the domain profile to block inbound
    # connections
    salt.utils.win_lgpo_netsh.set_firewall_settings(profile='domain',
                                                    inbound='blockinbound')

    # Set the outbound setting for the domain profile to allow outbound
    # connections
    salt.utils.win_lgpo_netsh.set_firewall_settings(profile='domain',
                                                    outbound='allowoutbound')

    # Set inbound/outbound settings for the domain profile in the group
    # policy to block inbound and allow outbound
    salt.utils.win_lgpo_netsh.set_firewall_settings(profile='domain',
                                                    inbound='blockinbound',
                                                    outbound='allowoutbound',
                                                    store='lgpo')
"""

import logging
import os
import re
import socket
import tempfile
from textwrap import dedent

import salt.modules.cmdmod
from salt.exceptions import CommandExecutionError

log = logging.getLogger(__name__)
__hostname__ = socket.gethostname()
__virtualname__ = "netsh"


# Although utils are often directly imported, it is also possible to use the
# loader.
def __virtual__():
    """
    Only load if on a Windows system
    """
    if not salt.utils.platform.is_windows():
        return False, "This utility only available on Windows"

    return __virtualname__


def _netsh_file(content):
    """
    helper function to get the results of ``netsh -f content.txt``

    Running ``netsh`` will drop you into a ``netsh`` prompt where you can issue
    ``netsh`` commands. You can put a series of commands in an external file and
    run them as if from a ``netsh`` prompt using the ``-f`` switch. That's what
    this function does.

    Args:

        content (str):
            The contents of the file that will be run by the ``netsh -f``
            command

    Returns:
        str: The text returned by the netsh command
    """
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="salt-", suffix=".netsh", delete=False, encoding="utf-8"
    ) as fp:
        fp.write(content)
    try:
        log.debug("%s:\n%s", fp.name, content)
        return salt.modules.cmdmod.run(f"netsh -f {fp.name}", python_shell=True)
    finally:
        os.remove(fp.name)


def _netsh_command(command, store):
    if store.lower() not in ("local", "lgpo"):
        raise ValueError(f"Incorrect store: {store}")
    # set the store for local or lgpo
    if store.lower() == "local":
        netsh_script = dedent(
            """\
            advfirewall
            set store local
            {}
        """.format(
                command
            )
        )
    else:
        netsh_script = dedent(
            """\
            advfirewall
            set store gpo = {}
            {}
        """.format(
                __hostname__, command
            )
        )
    return _netsh_file(content=netsh_script).splitlines()


def get_settings(profile, section, store="local"):
    """
    Get the firewall property from the specified profile in the specified store
    as returned by ``netsh advfirewall``.

    Args:

        profile (str):
            The firewall profile to query. Valid options are:

            - domain
            - public
            - private

        section (str):
            The property to query within the selected profile. Valid options
            are:

            - firewallpolicy : inbound/outbound behavior
            - logging : firewall logging settings
            - settings : firewall properties
            - state : firewalls state (on | off)

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        dict: A dictionary containing the properties for the specified profile

    Raises:
        CommandExecutionError: If an error occurs
        ValueError: If the parameters are incorrect
    """
    # validate input
    if profile.lower() not in ("domain", "public", "private"):
        raise ValueError(f"Incorrect profile: {profile}")
    if section.lower() not in ("state", "firewallpolicy", "settings", "logging"):
        raise ValueError(f"Incorrect section: {section}")
    if store.lower() not in ("local", "lgpo"):
        raise ValueError(f"Incorrect store: {store}")
    command = f"show {profile}profile {section}"
    # run it
    results = _netsh_command(command=command, store=store)
    # sample output:
    # Domain Profile Settings:
    # ----------------------------------------------------------------------
    # LocalFirewallRules                    N/A (GPO-store only)
    # LocalConSecRules                      N/A (GPO-store only)
    # InboundUserNotification               Disable
    # RemoteManagement                      Disable
    # UnicastResponseToMulticast            Enable

    # if it's less than 3 lines it failed
    if len(results) < 3:
        raise CommandExecutionError(f"Invalid results: {results}")
    ret = {}
    # Skip the first 2 lines. Add everything else to a dictionary
    for line in results[3:]:
        ret.update(dict(list(zip(*[iter(re.split(r"\s{2,}", line))] * 2))))

    # Remove spaces from the values so that `Not Configured` is detected
    # correctly
    for item in ret:
        ret[item] = ret[item].replace(" ", "")

    # special handling for firewallpolicy
    if section == "firewallpolicy":
        inbound, outbound = ret["Firewall Policy"].split(",")
        return {"Inbound": inbound, "Outbound": outbound}

    return ret


def get_all_settings(profile, store="local"):
    """
    Gets all the properties for the specified profile in the specified store

    Args:

        profile (str):
            The firewall profile to query. Valid options are:

            - domain
            - public
            - private

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        dict: A dictionary containing the specified settings
    """
    ret = dict()
    ret.update(get_settings(profile=profile, section="state", store=store))
    ret.update(get_settings(profile=profile, section="firewallpolicy", store=store))
    ret.update(get_settings(profile=profile, section="settings", store=store))
    ret.update(get_settings(profile=profile, section="logging", store=store))
    return ret


def get_all_profiles(store="local"):
    """
    Gets all properties for all profiles in the specified store

    Args:

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        dict: A dictionary containing the specified settings for each profile
    """
    return {
        "Domain Profile": get_all_settings(profile="domain", store=store),
        "Private Profile": get_all_settings(profile="private", store=store),
        "Public Profile": get_all_settings(profile="public", store=store),
    }


def set_firewall_settings(profile, inbound=None, outbound=None, store="local"):
    """
    Set the firewall inbound/outbound settings for the specified profile and
    store

    Args:

        profile (str):
            The firewall profile to configure. Valid options are:

            - domain
            - public
            - private

        inbound (str):
            The inbound setting. If ``None`` is passed, the setting will remain
            unchanged. Valid values are:

            - blockinbound
            - blockinboundalways
            - allowinbound
            - notconfigured

            Default is ``None``

        outbound (str):
            The outbound setting. If ``None`` is passed, the setting will remain
            unchanged. Valid values are:

            - allowoutbound
            - blockoutbound
            - notconfigured

            Default is ``None``

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        bool: ``True`` if successful

    Raises:
        CommandExecutionError: If an error occurs
        ValueError: If the parameters are incorrect
    """
    # Input validation
    if profile.lower() not in ("domain", "public", "private"):
        raise ValueError(f"Incorrect profile: {profile}")
    if inbound and inbound.lower() not in (
        "blockinbound",
        "blockinboundalways",
        "allowinbound",
        "notconfigured",
    ):
        raise ValueError(f"Incorrect inbound value: {inbound}")
    if outbound and outbound.lower() not in (
        "allowoutbound",
        "blockoutbound",
        "notconfigured",
    ):
        raise ValueError(f"Incorrect outbound value: {outbound}")
    if not inbound and not outbound:
        raise ValueError("Must set inbound or outbound")

    # You have to specify inbound and outbound setting at the same time
    # If you're only specifying one, you have to get the current setting for the
    # other
    if not inbound or not outbound:
        ret = get_settings(profile=profile, section="firewallpolicy", store=store)
        if not inbound:
            inbound = ret["Inbound"]
        if not outbound:
            outbound = ret["Outbound"]

    command = f"set {profile}profile firewallpolicy {inbound},{outbound}"

    results = _netsh_command(command=command, store=store)

    if results:
        raise CommandExecutionError(f"An error occurred: {results}")

    return True


def set_logging_settings(profile, setting, value, store="local"):
    """
    Configure logging settings for the Windows firewall.

    Args:

        profile (str):
            The firewall profile to configure. Valid options are:

            - domain
            - public
            - private

        setting (str):
            The logging setting to configure. Valid options are:

            - allowedconnections
            - droppedconnections
            - filename
            - maxfilesize

        value (str):
            The value to apply to the setting. Valid values are dependent upon
            the setting being configured. Valid options are:

            allowedconnections:

                - enable
                - disable
                - notconfigured

            droppedconnections:

                - enable
                - disable
                - notconfigured

            filename:

                - Full path and name of the firewall log file
                - notconfigured

            maxfilesize:

                - 1 - 32767 (Kb)
                - notconfigured

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        bool: ``True`` if successful

    Raises:
        CommandExecutionError: If an error occurs
        ValueError: If the parameters are incorrect
    """
    # Input validation
    if profile.lower() not in ("domain", "public", "private"):
        raise ValueError(f"Incorrect profile: {profile}")
    if setting.lower() not in (
        "allowedconnections",
        "droppedconnections",
        "filename",
        "maxfilesize",
    ):
        raise ValueError(f"Incorrect setting: {setting}")
    if setting.lower() in ("allowedconnections", "droppedconnections"):
        if value.lower() not in ("enable", "disable", "notconfigured"):
            raise ValueError(f"Incorrect value: {value}")
    # TODO: Consider adding something like the following to validate filename
    # https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta
    if setting.lower() == "maxfilesize":
        if value.lower() != "notconfigured":
            # Must be a number between 1 and 32767
            try:
                int(value)
            except ValueError:
                raise ValueError(f"Incorrect value: {value}")
            if not 1 <= int(value) <= 32767:
                raise ValueError(f"Incorrect value: {value}")
    # Run the command
    command = f"set {profile}profile logging {setting} {value}"
    results = _netsh_command(command=command, store=store)

    # A successful run should return an empty list
    if results:
        raise CommandExecutionError(f"An error occurred: {results}")

    return True


def set_settings(profile, setting, value, store="local"):
    """
    Configure firewall settings.

    Args:

        profile (str):
            The firewall profile to configure. Valid options are:

            - domain
            - public
            - private

        setting (str):
            The firewall setting to configure. Valid options are:

            - localfirewallrules
            - localconsecrules
            - inboundusernotification
            - remotemanagement
            - unicastresponsetomulticast

        value (str):
            The value to apply to the setting. Valid options are

            - enable
            - disable
            - notconfigured

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        bool: ``True`` if successful

    Raises:
        CommandExecutionError: If an error occurs
        ValueError: If the parameters are incorrect
    """
    # Input validation
    if profile.lower() not in ("domain", "public", "private"):
        raise ValueError(f"Incorrect profile: {profile}")
    if setting.lower() not in (
        "localfirewallrules",
        "localconsecrules",
        "inboundusernotification",
        "remotemanagement",
        "unicastresponsetomulticast",
    ):
        raise ValueError(f"Incorrect setting: {setting}")
    if value.lower() not in ("enable", "disable", "notconfigured"):
        raise ValueError(f"Incorrect value: {value}")

    # Run the command
    command = f"set {profile}profile settings {setting} {value}"
    results = _netsh_command(command=command, store=store)

    # A successful run should return an empty list
    if results:
        raise CommandExecutionError(f"An error occurred: {results}")

    return True


def set_state(profile, state, store="local"):
    """
    Configure the firewall state.

    Args:

        profile (str):
            The firewall profile to configure. Valid options are:

            - domain
            - public
            - private

        state (str):
            The firewall state. Valid options are:

            - on
            - off
            - notconfigured

        store (str):
            The store to use. This is either the local firewall policy or the
            policy defined by local group policy. Valid options are:

            - lgpo
            - local

            Default is ``local``

    Returns:
        bool: ``True`` if successful

    Raises:
        CommandExecutionError: If an error occurs
        ValueError: If the parameters are incorrect
    """
    # Input validation
    if profile.lower() not in ("domain", "public", "private"):
        raise ValueError(f"Incorrect profile: {profile}")
    if state.lower() not in ("on", "off", "notconfigured"):
        raise ValueError(f"Incorrect state: {state}")

    # Run the command
    command = f"set {profile}profile state {state}"
    results = _netsh_command(command=command, store=store)

    # A successful run should return an empty list
    if results:
        raise CommandExecutionError(f"An error occurred: {results}")

    return True
