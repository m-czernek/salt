"""
Wrapper around Server Density API
=================================

.. versionadded:: 2014.7.0
"""

import logging
import os
import tempfile

import salt.utils.json
from salt.exceptions import CommandExecutionError

try:
    import requests

    ENABLED = True
except ImportError:
    ENABLED = False

log = logging.getLogger(__name__)


def __virtual__():
    """
    Return virtual name of the module.

    :return: The virtual name of the module.
    """
    if not ENABLED:
        return (False, "The requests python module cannot be imported")
    return "serverdensity_device"


def get_sd_auth(val, sd_auth_pillar_name="serverdensity"):
    """
    Returns requested Server Density authentication value from pillar.

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.get_sd_auth <val>
    """
    sd_pillar = __pillar__.get(sd_auth_pillar_name)
    log.debug("Server Density Pillar: %s", sd_pillar)
    if not sd_pillar:
        log.error("Could not load %s pillar", sd_auth_pillar_name)
        raise CommandExecutionError(
            f"{sd_auth_pillar_name} pillar is required for authentication"
        )

    try:
        return sd_pillar[val]
    except KeyError:
        log.error("Could not find value %s in pillar", val)
        raise CommandExecutionError(f"{val} value was not found in pillar")


def _clean_salt_variables(params, variable_prefix="__"):
    """
    Pops out variables from params which starts with `variable_prefix`.
    """
    list(list(map(params.pop, [k for k in params if k.startswith(variable_prefix)])))
    return params


def create(name, **params):
    """
    Function to create device in Server Density. For more info, see the `API
    docs`__.

    .. __: https://apidocs.serverdensity.com/Inventory/Devices/Creating

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.create lama
        salt '*' serverdensity_device.create rich_lama group=lama_band installedRAM=32768
    """
    log.debug("Server Density params: %s", params)
    params = _clean_salt_variables(params)

    params["name"] = name
    api_response = requests.post(
        "https://api.serverdensity.io/inventory/devices/",
        params={"token": get_sd_auth("api_token")},
        data=params,
        timeout=120,
    )
    log.debug("Server Density API Response: %s", api_response)
    log.debug("Server Density API Response content: %s", api_response.content)
    if api_response.status_code == 200:
        try:
            return salt.utils.json.loads(api_response.content)
        except ValueError:
            log.error("Could not parse API Response content: %s", api_response.content)
            raise CommandExecutionError(
                f"Failed to create, API Response: {api_response}"
            )
    else:
        return None


def delete(device_id):
    """
    Delete a device from Server Density. For more information, see the `API
    docs`__.

    .. __: https://apidocs.serverdensity.com/Inventory/Devices/Deleting

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.delete 51f7eafcdba4bb235e000ae4
    """
    api_response = requests.delete(
        "https://api.serverdensity.io/inventory/devices/" + device_id,
        params={"token": get_sd_auth("api_token")},
        timeout=120,
    )
    log.debug("Server Density API Response: %s", api_response)
    log.debug("Server Density API Response content: %s", api_response.content)
    if api_response.status_code == 200:
        try:
            return salt.utils.json.loads(api_response.content)
        except ValueError:
            log.error("Could not parse API Response content: %s", api_response.content)
            raise CommandExecutionError(
                f"Failed to create, API Response: {api_response}"
            )
    else:
        return None


def ls(**params):
    """
    List devices in Server Density

    Results will be filtered by any params passed to this function. For more
    information, see the API docs on listing_ and searching_.

    .. _listing: https://apidocs.serverdensity.com/Inventory/Devices/Listing
    .. _searching: https://apidocs.serverdensity.com/Inventory/Devices/Searching

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.ls
        salt '*' serverdensity_device.ls name=lama
        salt '*' serverdensity_device.ls name=lama group=lama_band installedRAM=32768
    """
    params = _clean_salt_variables(params)

    endpoint = "devices"

    # Change endpoint if there are params to filter by:
    if params:
        endpoint = "resources"

    # Convert all ints to strings:
    for key, val in params.items():
        params[key] = str(val)

    api_response = requests.get(
        f"https://api.serverdensity.io/inventory/{endpoint}",
        params={
            "token": get_sd_auth("api_token"),
            "filter": salt.utils.json.dumps(params),
        },
        timeout=120,
    )
    log.debug("Server Density API Response: %s", api_response)
    log.debug("Server Density API Response content: %s", api_response.content)
    if api_response.status_code == 200:
        try:
            return salt.utils.json.loads(api_response.content)
        except ValueError:
            log.error(
                "Could not parse Server Density API Response content: %s",
                api_response.content,
            )
            raise CommandExecutionError(
                f"Failed to create, Server Density API Response: {api_response}"
            )
    else:
        return None


def update(device_id, **params):
    """
    Updates device information in Server Density. For more information see the
    `API docs`__.

    .. __: https://apidocs.serverdensity.com/Inventory/Devices/Updating

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.update 51f7eafcdba4bb235e000ae4 name=lama group=lama_band
        salt '*' serverdensity_device.update 51f7eafcdba4bb235e000ae4 name=better_lama group=rock_lamas swapSpace=512
    """
    params = _clean_salt_variables(params)

    api_response = requests.put(
        "https://api.serverdensity.io/inventory/devices/" + device_id,
        params={"token": get_sd_auth("api_token")},
        data=params,
        timeout=120,
    )
    log.debug("Server Density API Response: %s", api_response)
    log.debug("Server Density API Response content: %s", api_response.content)
    if api_response.status_code == 200:
        try:
            return salt.utils.json.loads(api_response.content)
        except ValueError:
            log.error(
                "Could not parse Server Density API Response content: %s",
                api_response.content,
            )
            raise CommandExecutionError(
                f"Failed to create, API Response: {api_response}"
            )
    else:
        return None


def install_agent(agent_key, agent_version=1):
    """
    Function downloads Server Density installation agent, and installs sd-agent
    with agent_key. Optionally the agent_version would select the series to
    use (defaults on the v1 one).

    CLI Example:

    .. code-block:: bash

        salt '*' serverdensity_device.install_agent c2bbdd6689ff46282bdaa07555641498
        salt '*' serverdensity_device.install_agent c2bbdd6689ff46282bdaa07555641498 2
    """
    work_dir = os.path.join(__opts__["cachedir"], "tmp")
    if not os.path.isdir(work_dir):
        os.mkdir(work_dir)
    install_file = tempfile.NamedTemporaryFile(dir=work_dir, suffix=".sh", delete=False)
    install_filename = install_file.name
    install_file.close()

    account_field = "account_url"
    url = "https://www.serverdensity.com/downloads/agent-install.sh"
    if agent_version == 2:
        account_field = "account_name"
        url = "https://archive.serverdensity.com/agent-install.sh"

    account = get_sd_auth(account_field)

    __salt__["cmd.run"](cmd=f"curl -L {url} -o {install_filename}", cwd=work_dir)
    __salt__["cmd.run"](cmd=f"chmod +x {install_filename}", cwd=work_dir)

    return __salt__["cmd.run"](
        cmd="{filename} -a {account} -k {agent_key}".format(
            filename=install_filename, account=account, agent_key=agent_key
        ),
        cwd=work_dir,
    )
