import logging
import pytest
import socket

from stacklight_tests.clients.prometheus.prometheus_client import PrometheusClient  # noqa

logger = logging.getLogger(__name__)


class TestPrometheusSmoke(object):
    def test_prometheus_container(self, salt_actions):
        prometheus_nodes = salt_actions.ping(
            "prometheus:alertmanager", tgt_type="pillar")

        def test_prometheus_container_up(node):
            status = salt_actions.run_cmd(
                node,
                "docker ps --filter name=monitoring_server "
                "--format '{{.Status}}'")[0]
            return "Up" in status

        assert any([test_prometheus_container_up(node)
                    for node in prometheus_nodes])

    def test_prometheus_datasource(self, prometheus_api):
        assert prometheus_api.get_all_measurements()

    def test_prometheus_relay(self, salt_actions):
        hosts = salt_actions.ping("I@prometheus:relay")
        if not hosts:
            pytest.skip("Prometheus relay is not installed in the cluster")
        backends = [h["host"] for h in salt_actions.get_pillar_item(
            hosts[0], "prometheus:relay:backends")[0]]
        port = salt_actions.get_pillar_item(
            hosts[0], "prometheus:relay:backends:port")[0]
        cmd = "curl -s {}:{}/metrics | awk '/^prometheus/{{print $1}}'"
        outputs = [salt_actions.run_cmd(hosts[0], cmd.format(b, port))[0]
                   for b in backends]
        assert len(set(outputs)) == 1

    def test_prometheus_lts(self, prometheus_api, salt_actions):
        hosts = salt_actions.ping("I@prometheus:relay")
        if not hosts:
            pytest.skip("Prometheus LTS is not used in the cluster")
        address = salt_actions.get_pillar_item(
            hosts[0], '_param:single_address')[0]
        port = salt_actions.get_pillar_item(
            hosts[0], "prometheus:server:bind:port")[0]
        prometheus_lts = PrometheusClient(
            "http://{0}:{1}/".format(address, port))

        logger.info("Checking that target for Prometheus LTS is up")
        q = 'up{job="prometheus_federation"}'
        output = prometheus_lts.get_query(q)
        logger.info('Got {} metrics for {} query'.format(output, q))
        msg = 'There are no metrics for query'.format(q)
        assert len(output), msg
        logger.info("Check value '1' for metrics {}".format(q))
        msg = 'Incorrect value in metric {}'
        for metric in output:
            assert '1' in metric['value'], msg.format(metric)

        logger.info("Comparing lists of measurements in Prometheus long term "
                    "storage and short term storage")
        sts_meas = prometheus_api.get_all_measurements()
        lts_meas = prometheus_lts.get_all_measurements()
        msg = (
            "Measurements in Prometheus short term storage "
            "and NOT in long term storage: {0}\n"
            "Measurements in Prometheus long term storage "
            "and NOT in short term storage: {1}".format(
                sts_meas.difference(lts_meas),
                lts_meas.difference(sts_meas))
        )
        assert sts_meas == lts_meas, msg


class TestAlertmanagerSmoke(object):
    def test_alertmanager_endpoint_availability(self, prometheus_config):
        """Check that alertmanager endpoint is available.

        Scenario:
            1. Get alertmanager endpoint
            2. Check that alertmanager endpoint is available
        Duration 1m
        """
        port = int(prometheus_config["prometheus_alertmanager"])
        alertmanager_ip = prometheus_config["prometheus_vip"]
        try:
            s = socket.socket()
            s.connect((alertmanager_ip, port))
            s.close()
            result = True
        except socket.error:
            result = False
        assert result

    def test_alertmanager_ha(self, salt_actions, prometheus_config):
        """Check alertmanager HA .

        Scenario:
            1. Stop 1 alertmanager replic
            2. Get alertmanager endpoint
            3. Check that alertmanager endpoint is available
        Duration 1m
        """
        prometheus_nodes = salt_actions.ping(
            "I@prometheus:server and I@docker:client")
        for host in prometheus_nodes:
            alertmanager_docker_id = salt_actions.run_cmd(
                host,
                "docker ps | grep alertmanager | awk '{print $1}'")[0]
            if alertmanager_docker_id:
                command = "docker kill " + str(alertmanager_docker_id)
                salt_actions.run_cmd(host, command)
                return TestAlertmanagerSmoke. \
                    test_alertmanager_endpoint_availability(self,
                                                            prometheus_config)
