"""
    :codeauthor: Rahul Handay <rahulha@saltstack.com>

    Test cases for salt.states.virtualenv_mod
"""

import os

import pytest

import salt.states.virtualenv_mod as virtualenv_mod
from tests.support.mock import MagicMock, patch


@pytest.fixture
def configure_loader_modules():
    return {virtualenv_mod: {"__env__": "base"}}


def test_managed():
    """
    Test to create a virtualenv and optionally manage it with pip
    """
    ret = {"name": "salt", "changes": {}, "result": False, "comment": ""}
    ret.update({"comment": "Virtualenv was not detected on this system"})
    assert virtualenv_mod.managed("salt") == ret

    mock1 = MagicMock(return_value="True")
    mock = MagicMock(return_value=False)
    mock2 = MagicMock(return_value="1.1")
    with patch.dict(
        virtualenv_mod.__salt__,
        {
            "virtualenv.create": True,
            "cp.is_cached": mock,
            "cp.cache_file": mock,
            "cp.hash_file": mock,
            "pip.freeze": mock1,
            "cmd.run_stderr": mock1,
            "pip.version": mock2,
        },
    ):
        mock = MagicMock(side_effect=[True, True, True, False, True, True])
        with patch.object(os.path, "exists", mock):
            ret.update({"comment": "pip requirements file 'salt://a' not found"})
            assert virtualenv_mod.managed("salt", None, "salt://a") == ret

            with patch.dict(virtualenv_mod.__opts__, {"test": True}):
                ret.update(
                    {
                        "changes": {"cleared_packages": "True", "old": "True"},
                        "comment": "Virtualenv salt is set to be cleared",
                        "result": None,
                    }
                )
                assert virtualenv_mod.managed("salt", clear=1) == ret
                ret.update(
                    {
                        "comment": "Virtualenv salt is already created",
                        "changes": {},
                        "result": True,
                    }
                )
                assert virtualenv_mod.managed("salt") == ret

                ret.update(
                    {
                        "comment": "Virtualenv salt is set to be created",
                        "result": None,
                    }
                )
                assert virtualenv_mod.managed("salt") == ret

            with patch.dict(virtualenv_mod.__opts__, {"test": False}):
                ret.update(
                    {
                        "comment": (
                            "The 'use_wheel' option is"
                            " only supported in pip between 1.4 and 9.0.3."
                            " The version of pip detected was 1.1."
                        ),
                        "result": False,
                    }
                )
                assert virtualenv_mod.managed("salt", use_wheel=1) == ret

                ret.update({"comment": "virtualenv exists", "result": True})
                assert virtualenv_mod.managed("salt") == ret
