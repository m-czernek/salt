"""
    :codeauthor: Rahul Handay <rahulha@saltstack.com>
"""

import pytest

import salt.states.tomcat as tomcat
from salt.modules import tomcat as tomcatmod
from tests.support.mock import MagicMock, patch


@pytest.fixture
def configure_loader_modules():
    return {tomcat: {"__env__": "base"}}


def test_war_deployed():
    """
    Test to enforce that the WAR will be deployed and
    started in the context path it will make use of WAR versions
    """
    ret = {"name": "salt", "changes": {}, "result": True, "comment": ""}
    mock_start = MagicMock(return_value="saltstack")
    mock_undeploy = MagicMock(side_effect=["FAIL", "saltstack"])
    mock_deploy = MagicMock(return_value="deploy")
    mock_ls = MagicMock(
        side_effect=[
            {"salt": {"version": "jenkins-1.20.4", "mode": "running"}},
            {"salt": {"version": "1"}},
            {"salt": {"version": "jenkins-1.2.4", "mode": "run"}},
            {"salt": {"version": "1"}},
            {"salt": {"version": "1"}},
            {"salt": {"version": "1"}},
        ]
    )
    with patch.dict(
        tomcat.__salt__,
        {
            "tomcat.ls": mock_ls,
            "tomcat.extract_war_version": tomcatmod.extract_war_version,
            "tomcat.start": mock_start,
            "tomcat.undeploy": mock_undeploy,
            "tomcat.deploy_war": mock_deploy,
        },
    ):
        ret.update({"comment": "salt with version 1.20.4 is already deployed"})
        assert tomcat.war_deployed("salt", "salt://jenkins-1.20.4.war") == ret

        with patch.dict(tomcat.__opts__, {"test": True}):
            ret.update(
                {
                    "changes": {
                        "deploy": "will deploy salt with version 1.2.4",
                        "undeploy": "undeployed salt with version 1",
                    },
                    "result": None,
                    "comment": "",
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war") == ret

        with patch.dict(tomcat.__opts__, {"test": False}):
            ret.update(
                {
                    "changes": {"start": "starting salt"},
                    "comment": "saltstack",
                    "result": False,
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war") == ret

            ret.update(
                {
                    "changes": {
                        "deploy": "will deploy salt with version 1.2.4",
                        "undeploy": "undeployed salt with version 1",
                    },
                    "comment": "FAIL",
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war") == ret

            ret.update(
                {
                    "changes": {"undeploy": "undeployed salt with version 1"},
                    "comment": "deploy",
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war") == ret


def test_war_deployed_no_version():
    """
    Tests that going from versions to no versions and back work, as well
    as not overwriting a WAR without version with another without version.
    """
    ret = {"name": "salt", "changes": {}, "result": None, "comment": ""}

    mock_deploy = MagicMock(return_value="deploy")
    mock_undeploy = MagicMock(return_value="SUCCESS")
    mock_ls_version = MagicMock(
        return_value={"salt": {"version": "1.2.4", "mode": "running"}}
    )
    mock_ls_no_version = MagicMock(
        return_value={"salt": {"version": "", "mode": "running"}}
    )

    with patch.dict(tomcat.__opts__, {"test": True}):
        with patch.dict(
            tomcat.__salt__,
            {
                "tomcat.ls": mock_ls_version,
                "tomcat.extract_war_version": tomcatmod.extract_war_version,
                "tomcat.deploy_war": mock_deploy,
                "tomcat.undeploy": mock_undeploy,
            },
        ):
            ret.update(
                {
                    "changes": {
                        "deploy": "will deploy salt with no version",
                        "undeploy": "undeployed salt with version 1.2.4",
                    },
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins.war") == ret

        with patch.dict(
            tomcat.__salt__,
            {
                "tomcat.ls": mock_ls_no_version,
                "tomcat.extract_war_version": tomcatmod.extract_war_version,
                "tomcat.deploy_war": mock_deploy,
                "tomcat.undeploy": mock_undeploy,
            },
        ):
            ret.update(
                {
                    "changes": {
                        "deploy": "will deploy salt with version 1.2.4",
                        "undeploy": "undeployed salt with no version",
                    },
                }
            )
            assert (
                tomcat.war_deployed("salt", "salt://jenkins.war", version="1.2.4")
                == ret
            )
            assert tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war") == ret
            ret.update(
                {
                    "changes": {},
                    "comment": "salt with no version is already deployed",
                    "result": True,
                }
            )
            assert tomcat.war_deployed("salt", "salt://jenkins.war") == ret
            assert (
                tomcat.war_deployed("salt", "salt://jenkins-1.2.4.war", version=False)
                == ret
            )


def test_wait():
    """
    Test to wait for the tomcat manager to load
    """
    ret = {
        "name": "salt",
        "changes": {},
        "result": True,
        "comment": "tomcat manager is ready",
    }
    mock = MagicMock(return_value=True)
    with patch.dict(
        tomcat.__salt__,
        {
            "tomcat.status": mock,
            "tomcat.extract_war_version": tomcatmod.extract_war_version,
        },
    ):
        assert tomcat.wait("salt") == ret


def test_mod_watch():
    """
    Test to the tomcat watcher function.
    """
    ret = {"name": "salt", "changes": {}, "result": False, "comment": "True"}
    mock = MagicMock(return_value="True")
    with patch.dict(
        tomcat.__salt__,
        {
            "tomcat.reload": mock,
            "tomcat.extract_war_version": tomcatmod.extract_war_version,
        },
    ):
        ret.update({"changes": {"salt": False}})
        assert tomcat.mod_watch("salt") == ret


def test_undeployed():
    """
    Test to enforce that the WAR will be un-deployed from the server
    """
    ret = {"name": "salt", "changes": {}, "result": False, "comment": "True"}
    mock = MagicMock(side_effect=[False, True, True, True, True])
    mock1 = MagicMock(
        side_effect=[
            {"salt": {"a": 1}},
            {"salt": {"version": 1}},
            {"salt": {"version": 1}},
            {"salt": {"version": 1}},
        ]
    )
    mock2 = MagicMock(side_effect=["FAIL", "saltstack"])
    with patch.dict(
        tomcat.__salt__,
        {
            "tomcat.status": mock,
            "tomcat.extract_war_version": tomcatmod.extract_war_version,
            "tomcat.ls": mock1,
            "tomcat.undeploy": mock2,
        },
    ):
        ret.update({"comment": "Tomcat Manager does not respond"})
        assert tomcat.undeployed("salt") == ret

        ret.update({"comment": "", "result": True})
        assert tomcat.undeployed("salt") == ret

        with patch.dict(tomcat.__opts__, {"test": True}):
            ret.update({"changes": {"undeploy": 1}, "result": None})
            assert tomcat.undeployed("salt") == ret

        with patch.dict(tomcat.__opts__, {"test": False}):
            ret.update({"changes": {"undeploy": 1}, "comment": "FAIL", "result": False})
            assert tomcat.undeployed("salt") == ret

            ret.update({"changes": {"undeploy": 1}, "comment": "", "result": True})
            assert tomcat.undeployed("salt") == ret
