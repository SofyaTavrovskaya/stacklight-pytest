import pytest


fluentd_loggers = {
    "haproxy": ("haproxy:proxy", 'haproxy.general'),
    "neutron": ("neutron:server", 'openstack.neutron'),
    "glance": ("glance:server", 'openstack.glance'),
    "keystone": ("keystone:server", 'openstack.keystone'),
    "heat": ("heat:server", 'openstack.heat'),
    "cinder": ("cinder:controller", 'openstack.cinder'),
    "nova": ("nova:controller", 'openstack.nova'),
    "rabbitmq": ("rabbitmq:cluster", 'rabbitmq'),
    "system": ("linux:system", 'systemd.systemd'),
    "zookeeper": ("opencontrail:control", 'opencontrail.zookeeper'),
    "cassandra": ("opencontrail:database", 'opencontrail.cassandra.system'),
    "opencontrail": ("opencontrail:common", 'opencontrail.contrail-control')
}


@pytest.mark.smoke
@pytest.mark.parametrize(argnames="input_data",
                         argvalues=fluentd_loggers.values(),
                         ids=fluentd_loggers.keys())
@pytest.mark.run(order=2)
def test_fluentd_logs(es_client, salt_actions, input_data):
    pillar, logger = input_data
    if not salt_actions.ping("fluentd:agent", tgt_type="pillar"):
        pytest.skip("Fluentd is not installed in the cluster")
    if not salt_actions.ping(pillar, tgt_type="pillar"):
        pytest.skip("No required nodes with pillar {}".format(pillar))

    assert logger in es_client.return_loggers()
