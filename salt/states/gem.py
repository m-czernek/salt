"""
Installation of Ruby modules packaged as gems
=============================================

A state module to manage rubygems. Gems can be set up to be installed
or removed. This module will use RVM or rbenv if they are installed. In that case,
you can specify what ruby version and gemset to target.

.. code-block:: yaml

    addressable:
      gem.installed:
        - user: rvm
        - ruby: jruby@jgemset
"""

import logging
import re

import salt.utils.versions

log = logging.getLogger(__name__)


def __virtual__():
    """
    Only load if gem module is available in __salt__
    """
    if "gem.list" in __salt__:
        return True
    return (False, "gem module could not be loaded")


def installed(
    name,  # pylint: disable=C0103
    ruby=None,
    gem_bin=None,
    user=None,
    version=None,
    rdoc=False,
    ri=False,
    pre_releases=False,
    proxy=None,
    source=None,
):  # pylint: disable=C0103
    """
    Make sure that a gem is installed.

    name
        The name of the gem to install

    ruby: None
        Only for RVM or rbenv installations: the ruby version and gemset to
        target.

    gem_bin: None
        Custom ``gem`` command to run instead of the default.
        Use this to install gems to a non-default ruby install. If you are
        using rvm or rbenv use the ruby argument instead.

    user: None
        The user under which to run the ``gem`` command

        .. versionadded:: 0.17.0

    version : None
        Specify the version to install for the gem.
        Doesn't play nice with multiple gems at once

    rdoc : False
        Generate RDoc documentation for the gem(s).

    ri : False
        Generate RI documentation for the gem(s).

    pre_releases : False
        Install pre-release version of gem(s) if available.

    proxy : None
        Use the specified HTTP proxy server for all outgoing traffic.
        Format: http://hostname[:port]

    source : None
        Use the specified HTTP gem source server to download gem.
        Format: http://hostname[:port]
    """
    ret = {"name": name, "result": None, "comment": "", "changes": {}}
    if ruby is not None and not (
        __salt__["rvm.is_installed"](runas=user)
        or __salt__["rbenv.is_installed"](runas=user)
    ):
        log.warning("Use of argument ruby found, but neither rvm or rbenv is installed")
    gems = __salt__["gem.list"](name, ruby, gem_bin=gem_bin, runas=user)
    if name in gems and version is not None:
        match = re.match(r"(>=|>|<|<=)", version)
        if match:
            # Grab the comparison
            cmpr = match.group()

            # Clear out 'default:' and any whitespace
            installed_version = re.sub("default: ", "", gems[name][0]).strip()

            # Clear out comparison from version and whitespace
            desired_version = re.sub(cmpr, "", version).strip()

            if salt.utils.versions.compare(installed_version, cmpr, desired_version):
                ret["result"] = True
                ret["comment"] = "Installed Gem meets version requirements."
                return ret
        else:
            if str(version) in gems[name]:
                ret["result"] = True
                ret["comment"] = "Gem is already installed."
                return ret
    elif name in gems and version is None:
        ret["result"] = True
        ret["comment"] = "Gem is already installed."
        return ret

    if __opts__["test"]:
        ret["comment"] = f"The gem {name} would have been installed"
        return ret
    if __salt__["gem.install"](
        name,
        ruby=ruby,
        gem_bin=gem_bin,
        runas=user,
        version=version,
        rdoc=rdoc,
        ri=ri,
        pre_releases=pre_releases,
        proxy=proxy,
        source=source,
    ):
        ret["result"] = True
        ret["changes"][name] = "Installed"
        ret["comment"] = "Gem was successfully installed"
    else:
        ret["result"] = False
        ret["comment"] = "Could not install gem."

    return ret


def removed(name, ruby=None, user=None, gem_bin=None):
    """
    Make sure that a gem is not installed.

    name
        The name of the gem to uninstall

    gem_bin : None
        Full path to ``gem`` binary to use.

    ruby : None
        If RVM or rbenv are installed, the ruby version and gemset to use.
        Ignored if ``gem_bin`` is specified.

    user: None
        The user under which to run the ``gem`` command

        .. versionadded:: 0.17.0
    """
    ret = {"name": name, "result": None, "comment": "", "changes": {}}

    if name not in __salt__["gem.list"](name, ruby, gem_bin=gem_bin, runas=user):
        ret["result"] = True
        ret["comment"] = "Gem is not installed."
        return ret

    if __opts__["test"]:
        ret["comment"] = f"The gem {name} would have been removed"
        return ret
    if __salt__["gem.uninstall"](name, ruby, gem_bin=gem_bin, runas=user):
        ret["result"] = True
        ret["changes"][name] = "Removed"
        ret["comment"] = "Gem was successfully removed."
    else:
        ret["result"] = False
        ret["comment"] = "Could not remove gem."
    return ret


def sources_add(name, ruby=None, user=None):
    """
    Make sure that a gem source is added.

    name
        The URL of the gem source to be added

    ruby: None
        For RVM or rbenv installations: the ruby version and gemset to target.

    user: None
        The user under which to run the ``gem`` command

        .. versionadded:: 0.17.0
    """
    ret = {"name": name, "result": None, "comment": "", "changes": {}}

    if name in __salt__["gem.sources_list"](ruby, runas=user):
        ret["result"] = True
        ret["comment"] = "Gem source is already added."
        return ret
    if __opts__["test"]:
        ret["comment"] = f"The gem source {name} would have been added."
        return ret
    if __salt__["gem.sources_add"](source_uri=name, ruby=ruby, runas=user):
        ret["result"] = True
        ret["changes"][name] = "Installed"
        ret["comment"] = "Gem source was successfully added."
    else:
        ret["result"] = False
        ret["comment"] = "Could not add gem source."
    return ret


def sources_remove(name, ruby=None, user=None):
    """
    Make sure that a gem source is removed.

    name
        The URL of the gem source to be removed

    ruby: None
        For RVM or rbenv installations: the ruby version and gemset to target.

    user: None
        The user under which to run the ``gem`` command

        .. versionadded:: 0.17.0
    """
    ret = {"name": name, "result": None, "comment": "", "changes": {}}

    if name not in __salt__["gem.sources_list"](ruby, runas=user):
        ret["result"] = True
        ret["comment"] = "Gem source is already removed."
        return ret

    if __opts__["test"]:
        ret["comment"] = "The gem source would have been removed."
        return ret

    if __salt__["gem.sources_remove"](source_uri=name, ruby=ruby, runas=user):
        ret["result"] = True
        ret["changes"][name] = "Removed"
        ret["comment"] = "Gem source was successfully removed."
    else:
        ret["result"] = False
        ret["comment"] = "Could not remove gem source."
    return ret
