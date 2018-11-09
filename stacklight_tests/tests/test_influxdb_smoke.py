def test_influxdb_installed(salt_actions, influxdb_client):
    """Smoke test that checks basic features of InfluxDb.

    Scenario:
        1. Check InfluxDB package is installed
        2. Check InfluxDB is up and running
        3. Check that InfluxDB is online and can serve requests

    Duration 1m
    """
    service = "influxdb"
    target = "influxdb:server"
    salt_actions.check_service_installed(service, target, tgt_type="pillar")
    salt_actions.check_service_running(service, target, tgt_type="pillar")
    if salt_actions.ping("I@prometheus:relay"):
        node = salt_actions.ping(target, tgt_type="pillar")[0]
        password = salt_actions.get_pillar_item(
            node, "_param:influxdb_admin_password")[0]
        influxdb_client.check_influxdb_online(
            user="root", password=password)
    else:
        influxdb_client.check_influxdb_online()


def test_influxdb_relay_installed(salt_actions):
    """Smoke test that checks basic features of InfluxDb.

    Scenario:
        1. Check InfluxDB relay package is installed
        2. Check InfluxDB relay is up and running

    Duration 1m
    """
    service = "influxdb-relay"
    target = "influxdb:relay"
    salt_actions.check_service_installed(service, target, tgt_type="pillar")
    salt_actions.check_service_running(service, target, tgt_type="pillar")
