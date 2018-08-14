import pytest

from stacklight_tests import utils


@pytest.mark.smoke
def test_alerta_smoke(alerta_api):
    alerta_api.get_count()

@pytest.mark.smoke
def test_alerta_alerts_consistency(prometheus_native_alerting, alerta_api):
    alerta_alerts = {"{0} {1}".format(i.event, i.resource)
                     for i in alerta_api.get_alerts({"status": "open"})}
    alertmanager_alerts = {"{0} {1}".format(i.name, i.instance)
                           for i in prometheus_native_alerting.list_alerts()}

    timeout_msg = ("Alerts in Alerta and NOT in AlertManager: {0}\n"
                   "Alerts in AlertManager and NOT in Alerta: {1}")

    utils.wait(lambda: alerta_alerts == alertmanager_alerts, timeout=6 * 60,
               timeout_msg=timeout_msg.format(
                   alerta_alerts.difference(alertmanager_alerts),
                   alertmanager_alerts.difference(alerta_alerts)))
