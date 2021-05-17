import pytest
import salt.loader
import salt.modules.win_lgpo as win_lgpo_module
import salt.states.win_lgpo as win_lgpo_state

pytestmark = [
    pytest.mark.windows_whitelisted,
    pytest.mark.skip_unless_on_windows,
    pytest.mark.destructive_test,
]


@pytest.fixture
def configure_loader_modules(minion_opts, modules):
    return {
        win_lgpo_state: {
            "__opts__": minion_opts,
            "__salt__": modules,
            "__utils__": salt.loader.utils(minion_opts),
        },
        win_lgpo_module: {
            "__opts__": {"cachedir": minion_opts["cachedir"]},
            "__salt__": modules,
            "__utils__": salt.loader.utils(minion_opts),
        }
    }


@pytest.fixture(scope="function")
def enable_legacy_auditing():
    # To test and use these policy settings we have to set one of the policies to Disabled
    # Location: Windows Settings -> Security Settings -> Local Policies -> Security Options
    # Policy: "Audit: Force audit policy subcategory settings..."
    # Short Name: SceNoApplyLegacyAuditPolicy
    test_setting = "Disabled"
    pre_setting = win_lgpo_module.get_policy(policy_name="SceNoApplyLegacyAuditPolicy", policy_class="machine")
    try:
        if pre_setting != test_setting:
            win_lgpo_module.set_computer_policy(name="SceNoApplyLegacyAuditPolicy", setting=test_setting)
            assert win_lgpo_module.get_policy(policy_name="SceNoApplyLegacyAuditPolicy", policy_class="machine") == test_setting
        yield
    finally:
        if win_lgpo_module.get_policy(policy_name="SceNoApplyLegacyAuditPolicy", policy_class="machine") != pre_setting:
            win_lgpo_module.set_computer_policy(name="SceNoApplyLegacyAuditPolicy", setting=pre_setting)


@pytest.fixture(scope="function")
def clear_policy():
    # Ensure the policy is not set
    test_setting = "No auditing"
    pre_setting = win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine")
    try:
        if pre_setting != test_setting:
            win_lgpo_module.set_computer_policy(name="Audit account management", setting=test_setting)
            assert win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine") == test_setting
        yield
    finally:
        if win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine") != pre_setting:
            win_lgpo_module.set_computer_policy(name="Audit account management", setting=pre_setting)


@pytest.fixture(scope="function")
def set_policy():
    # Ensure the policy is set
    test_setting = "Success"
    pre_setting = win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine")
    try:
        if pre_setting != test_setting:
            win_lgpo_module.set_computer_policy(name="Audit account management", setting=test_setting)
            assert win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine") == test_setting
        yield
    finally:
        if win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine") != pre_setting:
            win_lgpo_module.set_computer_policy(name="Audit account management", setting=pre_setting)


def _test_auditing(setting):
    """
    Helper function to set an audit setting and assert that it was successful
    """
    win_lgpo_state.set_(name="Audit account management", setting=setting, policy_class="machine")
    result = win_lgpo_module.get_policy(policy_name="Audit account management", policy_class="machine")
    assert result == setting


def test_audit_state_no_auditing(enable_legacy_auditing, set_policy):
    _test_auditing("No auditing")


def test_audit_state_success(enable_legacy_auditing, clear_policy):
    _test_auditing("Success")


def test_audit_state_failure(enable_legacy_auditing, clear_policy):
    _test_auditing("Failure")


def test_audit_state_success_and_failure(enable_legacy_auditing, clear_policy):
    _test_auditing("Success, Failure")
