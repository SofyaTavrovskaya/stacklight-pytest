import logging
import pytest

from stacklight_tests import utils

logger = logging.getLogger(__name__)


@pytest.mark.smoke
def test_alerta_smoke(alerta_api):
    alerta_api.get_count()


@pytest.mark.smoke
def test_alerta_alerts_consistency(prometheus_native_alerting, alerta_api):
    def check_alerts():
        alerta_alerts = {"{0} {1}".format(i.event, i.resource)
                         for i in alerta_api.get_alerts({"status": "open"})}
        alertmanager_alerts = {
            "{0} {1}".format(i.name, i.instance)
            for i in prometheus_native_alerting.list_alerts()}
        if alerta_alerts == alertmanager_alerts:
            return True
        else:
            logger.info(
                "Alerts in Alerta and NOT in AlertManager: {0}\n"
                "Alerts in AlertManager and NOT in Alerta: {1}".format(
                    alerta_alerts.difference(alertmanager_alerts),
                    alertmanager_alerts.difference(alerta_alerts)))
            return False

    utils.wait(check_alerts, interval=30, timeout=6 * 60,
               timeout_msg="Alerts in Alertmanager and Alerta incosistent")


@pytest.mark.smoke
def test_mongodb_installed(salt_actions):
    target = "I@mongodb:server"
    salt_actions.check_service_installed("mongodb", target)
    salt_actions.check_service_installed("mongodb-server", target)
    salt_actions.check_service_running("mongodb", target)


@pytest.mark.smoke
def test_mongodb_configuration(salt_actions, mongodb_api):
    node = salt_actions.ping("I@mongodb:server")[0]
    members = salt_actions.get_pillar_item(node, "mongodb:server:members")[0]
    port = salt_actions.get_pillar_item(node, "mongodb:server:bind:port")[0]
    repl = salt_actions.get_pillar_item(node, "mongodb:server:replica_set")[0]
    hosts = ["{}:{}".format(host["host"], port) for host in members]
    db = mongodb_api.alerta
    mongo_status = db.command("serverStatus")
    logger.debug(mongo_status)
    assert set(hosts) == set(mongo_status["repl"]["hosts"])
    assert repl == mongo_status["repl"]["setName"]
