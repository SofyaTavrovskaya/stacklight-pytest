import logging
import pytest
import re


logger = logging.getLogger(__name__)


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
    "cassandra": ("opencontrail:database", 'opencontrail.cassandra.*'),
    "opencontrail": ("opencontrail:common", 'opencontrail.contrail-*'),
    "elasticsearch": ("elasticsearch:server", 'elasticsearch.*'),
    "kibana": ("kibana:server", 'kibana.*'),
    "nginx": ("nginx:server", 'nginx.*'),
    "glusterfs": ("glusterfs:server", 'glusterfs.*'),
    "mysql": ("galera:master", "mysql.*")
}


@pytest.mark.smoke
@pytest.mark.parametrize(argnames="input_data",
                         argvalues=fluentd_loggers.values(),
                         ids=fluentd_loggers.keys())
@pytest.mark.run(order=-1)
def test_fluentd_logs(es_client, salt_actions, input_data):
    pillar, es_logger = input_data
    if not salt_actions.ping("fluentd:agent", tgt_type="pillar"):
        pytest.skip("Fluentd is not installed in the cluster")
    if not salt_actions.ping(pillar, tgt_type="pillar"):
        pytest.skip("No required nodes with pillar {}".format(pillar))

    logger_list = es_client.list_loggers()
    regex = re.compile(r'{}'.format(es_logger))

    logger.info("\nCheck logger with mask '{}' in logger list".format(
        regex.pattern))
    found_loggers = filter(regex.search, logger_list)
    logger.info("Found {} loggers for mask '{}'".format(
        found_loggers, regex.pattern))
    msg = "Loggers with mask '{}' not found in logger list {}".format(
        regex.pattern, logger_list)

    assert found_loggers, msg


def test_node_count_in_es(es_client, salt_actions):
    expected_nodes = salt_actions.ping(short=True)
    q = {"size": "0",
         "aggs": {
             "uniq_hostnames": {
                 "terms": {"field": "Hostname.keyword", "size": 500}}}}
    output = es_client.search(index='log-*', body=q)
    found_nodes = [host["key"] for host in
                   output["aggregations"]["uniq_hostnames"]["buckets"]]
    logger.info("\nFound the following nodes in Elasticsearch: \n{}".format(
        found_nodes))
    missing_nodes = []
    msg = (
        'Logs from not all nodes are in Elasticsearch. '
        'Found {} nodes, expected {}. Missing nodes: {}'.format(
            len(found_nodes), len(expected_nodes), missing_nodes)
    )
    for node in expected_nodes:
        if node not in found_nodes:
            missing_nodes.append(node)
    assert len(missing_nodes) == 0, msg
