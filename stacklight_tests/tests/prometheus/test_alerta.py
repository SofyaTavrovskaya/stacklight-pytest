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


@pytest.mark.skip(reason="Temporary disabling")
def test_alerts_metrics(salt_actions, prometheus_api):
    def filter_expr(s):
        for ch in ["(", ")", "[", "]"]:
            if ch in s:
                s = s.replace(ch, " ")
        m = list(set([i.strip(",") for i in s.split() if "_" in i]))
        for i in ["label_replace", "avg_over_time", "process_name"]:
            if i in m:
                m.remove(i)
        return m

    nodes = salt_actions.ping()
    for node in nodes:
        # Get list of alerts for the node
        grains = salt_actions.get_grains(node, "prometheus:server:alert",
                                         tgt_type="glob").values()[0]
        # Alerts to exclude because metrics for them may not exist
        exc = ["ErrorLogs", "KeystoneApiResponse", "NovaAggregate",
               "SshFailedLogins", "SystemDiskErrorsTooHigh"]
        alerts = [i for i in grains.keys() if not any(ex in i for ex in exc)]
        # Generate dict {Alertname: expression}
        metrics_dict = {i: grains[i]["if"] for i in alerts}
        # Generate dict {Alertname: [metrics]}
        d = {i: filter_expr(metrics_dict[i]) for i in metrics_dict.keys()}
        for alertname, metrics in d.items():
            for m in metrics:
                q = prometheus_api.get_query(m)
                assert q and len(prometheus_api.get_query(m)) != 0, \
                    "{} metric for {} alert not found for {} node".format(
                        m, alertname, node)
