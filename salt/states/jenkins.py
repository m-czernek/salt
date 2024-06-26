"""
Management of Jenkins
=====================

.. versionadded:: 2016.3.0

"""

import difflib
import io
import logging

# Import XML parser
import xml.etree.ElementTree as ET

import salt.utils.files
import salt.utils.stringutils
from salt.exceptions import CommandExecutionError

log = logging.getLogger(__name__)


def _elements_equal(e1, e2):
    if e1.tag != e2.tag:
        return False
    if e1.text != e2.text:
        return False
    if e1.tail != e2.tail:
        return False
    if e1.attrib != e2.attrib:
        return False
    if len(e1) != len(e2):
        return False
    return all(_elements_equal(c1, c2) for c1, c2 in zip(e1, e2))


def _fail(ret, msg):
    ret["comment"] = msg
    ret["result"] = False
    return ret


def present(name, config=None, **kwargs):
    """
    Ensure the job is present in the Jenkins configured jobs

    name
        The unique name for the Jenkins job

    config
        The Salt URL for the file to use for configuring the job
    """

    ret = {
        "name": name,
        "result": True,
        "changes": {},
        "comment": [f"Job {name} is up to date."],
    }

    if __salt__["jenkins.job_exists"](name):
        _current_job_config = __salt__["jenkins.get_job_config"](name)
        buf = io.StringIO(_current_job_config)
        oldXML = ET.fromstring(buf.read())

        cached_source_path = __salt__["cp.cache_file"](config, __env__)
        with salt.utils.files.fopen(cached_source_path) as _fp:
            newXML = ET.fromstring(salt.utils.stringutils.to_unicode(_fp.read()))
        if not _elements_equal(oldXML, newXML):
            diff = difflib.unified_diff(
                ET.tostringlist(oldXML, encoding="utf8", method="xml"),
                ET.tostringlist(newXML, encoding="utf8", method="xml"),
                lineterm="",
            )
            try:
                __salt__["jenkins.update_job"](name, config, __env__)
            except CommandExecutionError as exc:
                return _fail(ret, exc.strerror)
            else:
                ret["changes"] = "".join(diff)
                ret["comment"].append(f"Job '{name}' updated.")

    else:
        cached_source_path = __salt__["cp.cache_file"](config, __env__)
        with salt.utils.files.fopen(cached_source_path) as _fp:
            new_config_xml = salt.utils.stringutils.to_unicode(_fp.read())

        try:
            __salt__["jenkins.create_job"](name, config, __env__)
        except CommandExecutionError as exc:
            return _fail(ret, exc.strerror)

        buf = io.StringIO(new_config_xml)
        diff = difflib.unified_diff("", buf.readlines(), lineterm="")
        ret["changes"][name] = "".join(diff)
        ret["comment"].append(f"Job '{name}' added.")

    ret["comment"] = "\n".join(ret["comment"])
    return ret


def absent(name, **kwargs):
    """
    Ensure the job is absent from the Jenkins configured jobs

    name
        The name of the Jenkins job to remove
    """
    ret = {"name": name, "result": True, "changes": {}, "comment": []}

    if __salt__["jenkins.job_exists"](name):
        try:
            __salt__["jenkins.delete_job"](name)
        except CommandExecutionError as exc:
            return _fail(ret, exc.strerror)
        else:
            ret["comment"] = f"Job '{name}' deleted."
    else:
        ret["comment"] = f"Job '{name}' already absent."
    return ret
