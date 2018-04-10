import pytest


heka_loggers = {
    "haproxy": ("haproxy:proxy", 'system.haproxy'),
    "neutron": ("neutron:server", 'openstack.neutron'),
    "glance": ("glance:server", 'openstack.glance'),
    "keystone": ("keystone:server", 'openstack.keystone'),
    "heat": ("heat:server", 'openstack.heat'),
    "cinder": ("cinder:controller", 'openstack.cinder'),
    "nova": ("nova:controller", 'openstack.nova'),
    "rabbitmq": ("rabbitmq:cluster", 'rabbitmq.ctl01'),
    "system": ("linux:system", 'system.auth'),
    "zookeeper": ("opencontrail:control", 'contrail.zookeeper'),
    "cassandra": ("opencontrail:database", 'contrail.cassandra.system'),
    "contrail": ("opencontrail:common", 'contrail.discovery')
}


fluentd_loggers = {
    "haproxy": ("haproxy:proxy", 'haproxy.general'),
    "neutron": ("neutron:server", 'openstack.neutron'),
    "glance": ("glance:server", 'openstack.glance'),
    "keystone": ("keystone:server", 'openstack.keystone'),
    "heat": ("heat:server", 'openstack.heat'),
    "cinder": ("cinder:controller", 'openstack.cinder'),
    "nova": ("nova:controller", 'openstack.nova'),
    "rabbitmq": ("rabbitmq:cluster", 'rabbitmq'),
    "system": ("linux:system", 'systemd.source.systemd'),
    "zookeeper": ("opencontrail:control", 'opencontrail.zookeeper'),
    "cassandra": ("opencontrail:database", 'opencontrail.cassandra.system'),
    "opencontrail": ("opencontrail:common", 'opencontrail.discovery')
}


@pytest.mark.smoke
@pytest.mark.parametrize(argnames="input_data",
                         argvalues=fluentd_loggers.values(),
                         ids=fluentd_loggers.keys())
def test_heka_logs(es_client, salt_actions, input_data):
    pillar, logger = input_data
    if not salt_actions.ping("I@heka:log_collector"):
        pytest.skip("Heka is not installed in the cluster")
    if not salt_actions.ping(pillar, expr_form="pillar"):
        pytest.skip("No required nodes with pillar {}".format(pillar))

    assert logger in es_client.return_loggers()


@pytest.mark.smoke
@pytest.mark.parametrize(argnames="input_data",
                         argvalues=fluentd_loggers.values(),
                         ids=fluentd_loggers.keys())
def test_fluentd_logs(es_client, salt_actions, input_data):
    pillar, logger = input_data
    if not salt_actions.ping("fluentd:agent", expr_form="pillar"):
        pytest.skip("Fluentd is not installed in the cluster")
    if not salt_actions.ping(pillar, expr_form="pillar"):
        pytest.skip("No required nodes with pillar {}".format(pillar))

    assert logger in es_client.return_loggers()
