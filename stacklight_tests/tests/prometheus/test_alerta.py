import pytest


@pytest.mark.smoke
def test_alerta_smoke(alerta_api):
    pytest.skip("Alerta tests are skipped")
    alerta_api.get_count()

@pytest.mark.smoke
def test_alerta_alerts_consistency(prometheus_native_alerting, alerta_api):
    pytest.skip("Alerta tests are skipped")
    alerta_alerts = {"{0} {1}".format(i.event, i.resource)
                     for i in alerta_api.get_alerts({"status": "open"})}
    alertmanager_alerts = {"{0} {1}".format(i.name, i.instance)
                           for i in prometheus_native_alerting.list_alerts()}

    assert alerta_alerts == alertmanager_alerts, \
        ("Alerts in Alerta and NOT in AlertManager: {0}\n"
         "Alerts in AlertManager and NOT in Alerta: {1}".format(
            alerta_alerts.difference(alertmanager_alerts),
            alertmanager_alerts.difference(alerta_alerts)))
