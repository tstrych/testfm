import datetime
import pytest
import yaml
from fauxfactory import gen_string
from testfm.advanced import Advanced
from testfm.advanced_by_tag import AdvancedByTag
from testfm.constants import (
    DOGFOOD_ACTIVATIONKEY,
    DOGFOOD_ORG,
    katello_ca_consumer,
    RHN_PASSWORD,
    RHN_USERNAME,
    RHN_POOLID,
    sat_63_repo,
    sat_64_repo,
    sat_65_repo,
)
from testfm.decorators import capsule, stubbed
from testfm.log import logger


@pytest.fixture(scope='function')
def setup_sync_plan(request, ansible_module):
    sync_plan_name = gen_string('alpha')
    sync_date = datetime.datetime.today().strftime('%Y-%m-%d')
    setup = ansible_module.command(
        'hammer sync-plan create --name {0} --enabled true \
        --interval "weekly" --sync-date {1} --organization-id 1'.format(
            sync_plan_name, sync_date))
    for result in setup.values():
        assert result["rc"] == 0
    setup = ansible_module.command(
        'hammer --output csv sync-plan info --name {0} --organization-id 1'.format(
            sync_plan_name))
    sync_id = setup.values()[0]['stdout_lines'][1].split(',')[0]

    def teardown_sync_plan():
        teardown = ansible_module.command(
            'hammer sync-plan delete --name {0} --organization-id 1'.format(
                sync_plan_name))
        for result in teardown.values():
            assert result["rc"] == 0
    request.addfinalizer(teardown_sync_plan)
    return int(sync_id)


@pytest.fixture(scope='function')
def setup_install_pexpect(ansible_module):
    ansible_module.get_url(
        url='https://bootstrap.pypa.io/get-pip.py',
        dest='/root'
    )
    setup = ansible_module.command("python /root/get-pip.py")
    for result in setup.values():
        assert result["rc"] == 0
    setup = ansible_module.command("pip install pexpect")
    for result in setup.values():
        assert result["rc"] == 0


@pytest.fixture(scope='function')
def setup_teardown_repositories_setup(request, ansible_module):
    subscribed_to = str(ansible_module.command(
        'subscription-manager identity').values()[0]['stdout'])
    if "Quality Assurance" in subscribed_to:
        subscribed_to_cdn = True
    else:
            subscribed_to_cdn = False
    if subscribed_to_cdn is False:
        ansible_module.command('subscription-manager unregister')
        ansible_module.command('subscription-manager clean')
        ca_consumer = ansible_module.command(
            'yum list katello-ca-consumer*').values()[0]['stdout']
        if 'katello-ca-consumer' in ca_consumer:
            pkg_name = [t for t in ca_consumer.split() if t.startswith('katello-ca-consumer')][0]
            ansible_module.yum(name=pkg_name,
                               state='absent')
        ansible_module.command(
            'subscription-manager register --force --user="{0}" --password="{1}"'.format(
                RHN_USERNAME, RHN_PASSWORD))
        for pool_id in RHN_POOLID.split():
            ansible_module.command(
                'subscription-manager subscribe --pool={0}'.format(pool_id))

    def teardown_for_testcase():
        if subscribed_to_cdn is False:
            ansible_module.command('subscription-manager unregister')
            ansible_module.command('subscription-manager clean')
            ansible_module.command(
                'yum -y localinstall {0}'.format(katello_ca_consumer))
            ansible_module.command(
                'subscription-manager register --force --org="{0}" --activationkey="{1}"'.format(
                    DOGFOOD_ORG, DOGFOOD_ACTIVATIONKEY))

    request.addfinalizer(teardown_for_testcase)


def test_positive_foreman_maintain_service_restart(ansible_module):
    """Restart service using advanced procedure run

    :id: 64d3c78e-d602-43d6-bf77-f31135ed019e

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run service-restart

    :expectedresults: Katello-service should restart.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_service_restart())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_maintain_hammer_setup(setup_install_pexpect, ansible_module):
    """Hammer setup using advanced procedure

    :id: 236171c0-5185-465e-9eec-e15dfefb41c3

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Change password for user to any string
        2. Run advanced procedure run hammer-setup
        3. Change password to original password

    :expectedresults: Hammer setup should successful.

    :CaseImportance: Critical
    """
    try:
        setup = ansible_module.command("hammer -u admin -p changeme"
                                       " user update"
                                       " --login admin "
                                       "--password 'JMNBzJ*a-4;XH!C~'")
        for result in setup.values():
            logger.info(result)
            assert result["rc"] == 0
        output = ansible_module.expect(
            command=Advanced.run_hammer_setup(),
            responses={"Hammer admin password: ": "JMNBzJ*a-4;XH!C~"}
        )
        for result in output.values():
            logger.info(result)
            assert result["rc"] == 0
    finally:
        teardown = ansible_module.command("hammer -u admin "
                                          "-p 'JMNBzJ*a-4;XH!C~'"
                                          " user update --login admin"
                                          " --password 'changeme'")
        for result in teardown.values():
            logger.info(result)
            assert result["rc"] == 0


@stubbed
def test_positive_foreman_maintain_packages_update(ansible_module):
    """Packages update using advanced procedure run

    :id: d56523d7-7042-40e1-a96e-db8f33b960e5

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run packages-update

    :expectedresults: packages should update.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_packages_update())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_maintain_disable_maintenance_mode(ansible_module):
    """Disable maintenance mode using advanced procedure run

    :id: 3a58ce93-631e-42b6-9b41-1cb620f351e6

    :setup:
        1. foreman-maintain should be installed.
        2. maintenance mode should be enabled.

    :steps:
        1. Run foreman-maintain advanced procedure run maintenance-mode-disable

    :expectedresults: iptables rules should remove.

    :CaseImportance: Critical
    """
    setup = ansible_module.command(Advanced.run_enable_maintenance_mode())
    for result in setup.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
    contacted = ansible_module.command(Advanced.run_disable_maintenance_mode())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
    check_iptables = ansible_module.command("iptables -L")
    for rules in check_iptables.values():
        logger.info(rules['stdout'])
        assert "FOREMAN_MAINTAIN" not in rules['stdout']


def test_positive_foreman_maintain_enable_maintenance_mode(ansible_module):
    """Enable maintenance mode using advanced procedure run

    :id: a37c78da-430d-48be-b94a-c25699bddb02

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run maintenance-mode-enable

    :expectedresults: iptables rules should add.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_enable_maintenance_mode())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
    check_iptables = ansible_module.command("iptables -L")
    for rules in check_iptables.values():
        logger.info(result['stdout'])
        assert "FOREMAN_MAINTAIN" in rules['stdout']
    teardown = ansible_module.command(Advanced.run_disable_maintenance_mode())
    for result in teardown.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_taks_delete_old(ansible_module):
    """Delete old foreman-tasks using advanced procedure run

    :id: c5deaf67-8fa9-43a6-bf62-1c0d6be63a85

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        foreman-tasks-delete --state old

    :expectedresults: Old foreman tasks should delete.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_foreman_tasks_delete({
        u'state': 'old'
    }))
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_taks_delete_planning(ansible_module):
    """Delete planning foreman-tasks using advanced procedure run

    :id: 447f5b05-b6a2-4f3a-8e89-8281995ca1cf

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        foreman-tasks-delete --state planning

    :expectedresults: foreman tasks in planning state should delete.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_foreman_tasks_delete({
        u'state': 'planning'
    }))
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_taks_delete_pending(ansible_module):
    """Delete pending foreman-tasks using advanced procedure run

    :id: 6bd3af66-9910-48c4-8cbb-69c3ddd18d6c

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        foreman-tasks-delete --state pending

    :expectedresults: foreman tasks in pending state should delete.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_foreman_tasks_delete({
        u'state': 'pending'
    }))
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_task_resume(ansible_module):
    """Resume paused foreman-tasks using advanced procedure run

    :id: e9afe55b-e3a4-425a-8bfd-a8df6674e516

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        foreman-tasks-resume

    :expectedresults: foreman tasks in paused state should resume.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(Advanced.run_foreman_tasks_resume())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']


def test_positive_foreman_tasks_ui_investigate(setup_install_pexpect, ansible_module):
    """Run foreman-tasks-ui-investigate using advanced procedure run

    :id: 3b4f69c6-c0a1-42e3-a099-8a6e26280d17

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        foreman-tasks-ui-investigate

    :expectedresults: procedure foreman-tasks-ui-investigate should work.

    :CaseImportance: Critical
    """
    output = ansible_module.expect(
        command=Advanced.run_foreman_tasks_ui_investigate(),
        responses={"press ENTER after the tasks are resolved.": " "}
    )
    for result in output.values():
        logger.info(result)
        assert result["rc"] == 0


def test_positive_sync_plan_disable_enable(setup_sync_plan, ansible_module):
    """Run sync-plans-enable and sync-plans-disable
    using advanced procedure run.

    :id: 865df1e1-1189-437c-8451-22d772ff97d4

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure run
        sync-plans-disable
        2. Run foreman-maintain advanced procedure run
        sync-plans-enable

    :expectedresults: procedure sync-plans-enable should work.

    :CaseImportance: Critical
    """
    sat_hostname = ''
    for facts in ansible_module.setup().items():
        sat_hostname = facts[0]
    contacted = ansible_module.command(Advanced.run_sync_plans_disable())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert result["rc"] == 0
        assert "FAIL" not in result['stdout']
    ansible_module.fetch(
        src="/var/lib/foreman-maintain/data.yml",
        dest="./"
    )
    with open('./{0}/var/lib/foreman-maintain/data.yml'.format(sat_hostname)) as f:
        data_yml = yaml.safe_load(f)
    assert setup_sync_plan in data_yml[':default'][':sync_plans'][':disabled']

    contacted = ansible_module.command(Advanced.run_sync_plans_enable())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert result["rc"] == 0
        assert "FAIL" not in result['stdout']
    ansible_module.fetch(
        src="/var/lib/foreman-maintain/data.yml",
        dest="./"
    )
    with open('./{0}/var/lib/foreman-maintain/data.yml'.format(sat_hostname)) as f:
        data_yml = yaml.safe_load(f)
    assert setup_sync_plan in data_yml[':default'][':sync_plans'][':enabled']


def test_positive_procedure_by_tag_check_migrations(ansible_module):
    """Run pre-migrations and post-migrations using advanced
    procedure by-tag

    :id: 65cacca0-f142-4a63-a644-01f76120f16c

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure by-tag
        pre-migrations

        2. Run foreman-maintain advanced procedure by-tag
        post-migrations

    :expectedresults: procedures of pre-migrations tag and
     post-migrations tag should work.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(AdvancedByTag.pre_migrations())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
    check_iptables = ansible_module.command("iptables -L")
    for rules in check_iptables.values():
        logger.info(rules['stdout'])
        assert "FOREMAN_MAINTAIN" in rules['stdout']
    teardown = ansible_module.command(AdvancedByTag.post_migrations())
    for result in teardown.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
    check_iptables = ansible_module.command("iptables -L")
    for rules in check_iptables.values():
        logger.info(rules['stdout'])
        assert "FOREMAN_MAINTAIN" not in rules['stdout']


@capsule
def test_positive_procedure_by_tag_restore_confirmation(ansible_module):
    """Run restore_confirmation using advanced procedure by-tag

    :id: f9e10352-04fb-49ba-8346-5b02e64fd028

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Run foreman-maintain advanced procedure by-tag
        restore

    :expectedresults: procedure restore_confirmation should work.

    :CaseImportance: Critical
    """
    contacted = ansible_module.command(AdvancedByTag.restore([
        '--assumeyes']))
    for result in contacted.values():
        logger.info(result['stdout'])
        assert 'FAIL' not in result['stdout']
        assert result['rc'] == 0


def test_positive_sync_plan_with_hammer_defaults(ansible_module):
    """Verify that sync plan is disabled and enabled
    with hammer defaults set.

    :id: b25734c8-470f-4cad-bc56-5c0f75aa7499

    :setup:
        1. foreman-maintain should be installed.

    :steps:
        1. Setup hammer on system with defaults set

        2. Run foreman-maintain advanced procedure run sync-plans-enable

    :expectedresults: sync plans should get disabled and enabled.

    :CaseImportance: Critical
    """
    setup = ansible_module.command(
        "hammer defaults add --param-name organization_id --param-value 1")
    assert setup.values()[0]["rc"] == 0
    contacted = ansible_module.command(Advanced.run_sync_plans_disable())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
        assert result['rc'] == 0
    contacted = ansible_module.command(Advanced.run_sync_plans_enable())
    for result in contacted.values():
        logger.info(result['stdout'])
        assert "FAIL" not in result['stdout']
        assert result['rc'] == 0
    teardown = ansible_module.command(
        "hammer defaults delete --param-name organization_id")
    assert teardown.values()[0]["rc"] == 0


def test_positive_repositories_setup(setup_teardown_repositories_setup, ansible_module):
    """Verify that all required repositories gets enabled.
    :id: e32fee2d-2a1f-40ed-9f94-515f75511c5a
    :setup:
        1. foreman-maintain should be installed.
    :steps:
        1. Run 'foreman-maintain advanced procedure run repositories-setup --version 6.y
    :BZ: 1684730
    :expectedresults: Required repositories should get enabled
    :CaseImportance: Critical
    """
    for ver in ['6.3', '6.4', '6.5']:
        contacted = ansible_module.command(Advanced.run_repositories_setup({
            'version': ver
        }))
        for result in contacted.values():
            logger.info(result['stdout'])
            assert "FAIL" not in result['stdout']
            assert result['rc'] == 0
        contacted = ansible_module.command('yum repolist')
        for result in contacted.values():
            logger.info(result['stdout'])
            if ver == '6.3':
                for repo in sat_63_repo:
                    assert repo in result['stdout']
            if ver == '6.4':
                for repo in sat_64_repo:
                    assert repo in result['stdout']
            if ver == '6.5':
                for repo in sat_65_repo:
                    assert repo in result['stdout']
