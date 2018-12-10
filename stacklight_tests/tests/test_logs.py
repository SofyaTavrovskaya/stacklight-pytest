import logging
import pytest
import re


logger = logging.getLogger(__name__)


fluentd_loggers = {
    "calico": ("I@kubernetes:master:network:calico:enabled:True",
               "kubernetes.calico.*"),
    "cassandra": ("I@opencontrail:database", 'opencontrail.cassandra.*'),
    "cinder": ("I@cinder:controller", 'openstack.cinder'),
    "elasticsearch": ("I@elasticsearch:server", 'elasticsearch.*'),
    "glance": ("I@glance:server", 'openstack.glance'),
    "glusterfs": ("I@glusterfs:server", 'glusterfs.*'),
    "haproxy": ("I@haproxy:proxy", 'haproxy.general'),
    "heat": ("I@heat:server", 'openstack.heat'),
    "keystone": ("I@keystone:server", 'openstack.keystone'),
    "kibana": ("I@kibana:server", 'kibana.*'),
    "kubernetes": ("I@kubernetes:pool", "kubernetes.*"),
    "neutron": ("I@neutron:server", 'openstack.neutron'),
    "nginx": ("I@nginx:server", 'nginx.*'),
    "nova": ("I@nova:controller", 'openstack.nova'),
    "opencontrail": ("I@opencontrail:common", 'opencontrail.contrail-*'),
    "rabbitmq": ("I@rabbitmq:cluster", 'rabbitmq'),
    "system": ("I@linux:system", 'systemd.systemd'),
    "zookeeper": ("I@opencontrail:control", 'opencontrail.zookeeper'),
}


@pytest.mark.run(order=1)
def test_log_helper(salt_actions):
    # Helper methods to generate logs that may not be present right after
    # deployment
    kibana_nodes = salt_actions.ping("I@kibana:server")
    log_address = salt_actions.get_pillar_item(
        kibana_nodes[0], "_param:stacklight_log_address")[0]
    salt_actions.run_cmd(
        kibana_nodes[0], "curl -XGET http://{}:5601/status -I".format(
            log_address))
    nginx_nodes = salt_actions.ping("I@nginx:server")
    if nginx_nodes:
        salt_actions.run_cmd(
            nginx_nodes[0], "curl http://127.0.0.1/nginx_status")
        salt_actions.run_cmd(
            nginx_nodes[0], "curl http://127.0.0.1:15010/nginx_status")


@pytest.mark.smoke
@pytest.mark.parametrize(argnames="input_data",
                         argvalues=fluentd_loggers.values(),
                         ids=fluentd_loggers.keys())
@pytest.mark.run(order=-1)
def test_fluentd_logs(es_client, salt_actions, input_data):
    pillar, es_logger = input_data
    if not salt_actions.ping("I@fluentd:agent"):
        pytest.skip("Fluentd is not installed in the cluster")
    if not salt_actions.ping(pillar):
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
