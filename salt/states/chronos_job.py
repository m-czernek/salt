"""
Configure Chronos jobs via a salt proxy.

.. code-block:: yaml

    my_job:
      chronos_job.config:
        - config:
            schedule: "R//PT2S"
            command: "echo 'hi'"
            owner: "me@example.com"

.. versionadded:: 2015.8.2
"""

import copy
import logging

import salt.utils.configcomparer

__proxyenabled__ = ["chronos"]
log = logging.getLogger(__file__)


def config(name, config):
    """
    Ensure that the chronos job with the given name is present and is configured
    to match the given config values.

    :param name: The job name
    :param config: The configuration to apply (dict)
    :return: A standard Salt changes dictionary
    """
    # setup return structure
    ret = {
        "name": name,
        "changes": {},
        "result": False,
        "comment": "",
    }

    # get existing config if job is present
    existing_config = None
    if __salt__["chronos.has_job"](name):
        existing_config = __salt__["chronos.job"](name)["job"]

    # compare existing config with defined config
    if existing_config:
        update_config = copy.deepcopy(existing_config)
        salt.utils.configcomparer.compare_and_update_config(
            config,
            update_config,
            ret["changes"],
        )
    else:
        # the job is not configured--we need to create it from scratch
        ret["changes"]["job"] = {
            "new": config,
            "old": None,
        }
        update_config = config

    if ret["changes"]:
        # if the only change is in schedule, check to see if patterns are equivalent
        if "schedule" in ret["changes"] and len(ret["changes"]) == 1:
            if (
                "new" in ret["changes"]["schedule"]
                and "old" in ret["changes"]["schedule"]
            ):
                new = ret["changes"]["schedule"]["new"]
                log.debug("new schedule: %s", new)
                old = ret["changes"]["schedule"]["old"]
                log.debug("old schedule: %s", old)
                if new and old:
                    _new = new.split("/")
                    log.debug("_new schedule: %s", _new)
                    _old = old.split("/")
                    log.debug("_old schedule: %s", _old)
                    if len(_new) == 3 and len(_old) == 3:
                        log.debug(
                            "_new[0] == _old[0]: %s",
                            str(_new[0]) == str(_old[0]),
                        )
                        log.debug(
                            "_new[2] == _old[2]: %s",
                            str(_new[2]) == str(_old[2]),
                        )
                        if str(_new[0]) == str(_old[0]) and str(_new[2]) == str(
                            _old[2]
                        ):
                            log.debug("schedules match--no need for changes")
                            ret["changes"] = {}

    # update the config if we registered any changes
    log.debug("schedules match--no need for changes")
    if ret["changes"]:
        # if test report there will be an update
        if __opts__["test"]:
            ret["result"] = None
            ret["comment"] = f"Chronos job {name} is set to be updated"
            return ret

        update_result = __salt__["chronos.update_job"](name, update_config)
        if "exception" in update_result:
            ret["result"] = False
            ret["comment"] = "Failed to update job config for {}: {}".format(
                name,
                update_result["exception"],
            )
            return ret
        else:
            ret["result"] = True
            ret["comment"] = f"Updated job config for {name}"
            return ret
    ret["result"] = True
    ret["comment"] = f"Chronos job {name} configured correctly"
    return ret


def absent(name):
    """
    Ensure that the chronos job with the given name is not present.

    :param name: The app name
    :return: A standard Salt changes dictionary
    """
    ret = {"name": name, "changes": {}, "result": False, "comment": ""}
    if not __salt__["chronos.has_job"](name):
        ret["result"] = True
        ret["comment"] = f"Job {name} already absent"
        return ret
    if __opts__["test"]:
        ret["result"] = None
        ret["comment"] = f"Job {name} is set to be removed"
        return ret
    if __salt__["chronos.rm_job"](name):
        ret["changes"] = {"job": name}
        ret["result"] = True
        ret["comment"] = f"Removed job {name}"
        return ret
    else:
        ret["result"] = False
        ret["comment"] = f"Failed to remove job {name}"
        return ret
