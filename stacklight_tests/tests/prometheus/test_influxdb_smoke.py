def check_service_installed(salt_actions, name, tgt):
    """Checks that service is installed on nodes with provided role."""
    nodes = salt_actions.ping(tgt, expr_form="pillar")
    for node in nodes:
        output = salt_actions.run_cmd(node, "dpkg-query -l {}".format(name))
        err = "Package {} is not installed on the {} node"
        assert "no packages found" not in output[0], err.format(
            name, node)


def check_service_running(salt_actions, name, tgt):
    """Checks that service is running on nodes with provided role."""
    nodes = salt_actions.ping(tgt, expr_form="pillar")
    for node in nodes:
        err = "Service {} is stopped on the {} node"
        assert salt_actions.service_status(node, name).values()[0], err.format(
            name, node)


class TestInfluxDbSmoke(object):

    def test_influxdb_installed(self, salt_actions, influxdb_client):
        """Smoke test that checks basic features of InfluxDb.

        Scenario:
            1. Check InfluxDB package is installed
            2. Check InfluxDB is up and running
            3. Check that InfluxDB is online and can serve requests

        Duration 1m
        """
        service = "influxdb"
        target = "influxdb:server"
        check_service_installed(salt_actions, service, target)
        check_service_running(salt_actions, service, target)
        if salt_actions.ping("I@prometheus:relay"):
            node = salt_actions.ping(target, expr_form="pillar")[0]
            password = salt_actions.get_pillar_item(
                node, "_param:influxdb_admin_password")[0]
            influxdb_client.check_influxdb_online(
                user="root", password=password)
        else:
            influxdb_client.check_influxdb_online()

    def test_influxdb_relay_installed(self, salt_actions):
        """Smoke test that checks basic features of InfluxDb.

        Scenario:
            1. Check InfluxDB relay package is installed
            2. Check InfluxDB relay is up and running

        Duration 1m
        """
        service = "influxdb-relay"
        target = "influxdb:relay"
        check_service_installed(salt_actions, service, target)
        check_service_running(salt_actions, service, target)
