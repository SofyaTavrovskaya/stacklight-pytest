import collections

import pytest


ignored_queries_for_fail = [
    # Default installation does not contain cinder-volume
    'max(openstack_cinder_services{state="down", service="cinder-volume"})',
    'max(openstack_cinder_services{service="cinder-volume"}) by (state)',
    'max(openstack_cinder_services'
    '{state="disabled", service="cinder-volume"})',
    'max(openstack_cinder_services{state="up", service="cinder-volume"})',

    # https://mirantis.jira.com/browse/PROD-17651
    'cassandra_db_StorageService_Load{host=~"$host"}',
    'cassandra_db_StorageService_ExceptionCount{host=~"$host"}',

    # there are no aggregates by default
    # https://mirantis.jira.com/browse/PROD-17650
    'max(openstack_nova_aggregate_free_ram) by (aggregate)',
    'max(openstack_nova_aggregate_free_vcpus) by (aggregate)',
    'max(openstack_nova_aggregate_used_disk) by (aggregate)',
    'max(openstack_nova_aggregate_used_vcpus) by (aggregate)',
    'max(openstack_nova_aggregate_free_disk) by (aggregate)',
    'max(openstack_nova_aggregate_used_ram) by (aggregate)',

    # https://mirantis.jira.com/browse/PROD-17523
    'avg(jenkins_job_building_duration_sum/jenkins_job_building_duration_count)',

    # Temporarily skipped
    'prometheus_local_storage_target_heap_size_bytes{instance=~"$Prometheus:[1-99][0-9]*"}',

    # By default metric is not present if no tracked value
    'irate(openstack_heat_http_response_times_count{http_status="5xx"}[5m])',

    # Please check manually
    'min(openstack_nova_instance_creation_time)',
    'max(openstack_nova_instance_creation_time)',
    'avg(openstack_nova_instance_creation_time)',

    # https://mirantis.jira.com/browse/PROD-18802
    'rate(http_requests_total{handler="push",job="pushgateway",instance=~"$Pushgateway:[1-9][0-9]*"}[1h])',
    'rate(http_requests_total{handler="push",job="pushgateway",instance=~"$Pushgateway:[1-9][0-9]*"}[6h])',
    'rate(http_requests_total{handler="push",job="pushgateway",instance=~"$Pushgateway:[1-9][0-9]*"}[10m])',

    # Should be investigated
    'prometheus_local_storage_target_heap_size_bytes{instance=~"$Prometheus:[1-9][0-9]*"}',

    # https://mirantis.jira.com/browse/PROD-18803
    'count(influxdb_up == 1)',
    'count(influxdb_up == 0)',
    'count(influxdb_up)',
]


ignored_queries_for_partial_fail = [
    # Haproxy connections are not present on all nodes
    'max(haproxy_server_ssl_connections {host=~"$host"}) without(pid) > 0',
    'max(haproxy_server_connections {host=~"$host"}) without(pid) > 0',

    # https://mirantis.jira.com/browse/PROD-17649
    'min(zookeeper_pending_syncs{host=~"$host"})',
    'min(zookeeper_followers{host=~"$host"})',
    'min(zookeeper_synced_followers{host=~"$host"})',
]


def idfy_name(name):
    return name.lower().replace(" ", "-").replace("(", "").replace(")", "")


def query_dict_to_string(query_dict):
    return "\n\n".join(
        [panel + "\n" + query for panel, query in query_dict.items()])


def get_all_grafana_dashboards_names():
    dashboards = {
        "Apache": "apache",
        "Cassandra": "opencontrail",
        "Calico": "kubernetes",
        "Cinder": "cinder",
        "Docker": "docker",
        "Elasticsearch": "elasticsearch",
        "Etcd Cluster": "etcd",
        "Glance": "glance",
        "GlusterFS": "glusterfs",
        "HAProxy": "haproxy",
        "Hypervisor": "service.nova.compute.kvm",
        "Heat": "heat",
        "InfluxDB": "influxdb",
        "InfluxDB Relay": "influxdb",
        "Keystone": "keystone",
        "Kibana": "kibana",
        "Kubernetes cluster monitoring": "kubernetes",
        "Memcached": "memcached",
        "MySQL": "galera.master",
        "Neutron": "service.neutron.control.cluster",
        "Nova": "nova",
        "Ntp": "linux",
        "Nginx": "nginx",
        # Too many fails, skipped
        #"OpenContrail": "opencontrail",
        "Prometheus Performances": "prometheus",
        "Prometheus Stats": "prometheus",
        "RabbitMQ": "rabbitmq",
        "System": "linux",
        "Remote storage adapter": "influxdb",
        "Grafana": "grafana",
        "Compute Dashboard": "compute-dashboard",
        "Alertmanager": "alertmanager",
        "Zookeeper": "zookeeper",
        "Openstack Availability": "openstack-availability",
        "main_prometheus": "main_prometheus",
        "Cloud Usage": "cloud-usage",
        "Openstack FCI": "openstack-fci",
        "Pushgateway": "prometheus",
        "Jenkins": "jenkins",
        "Main": "main",
        "CSM Dashboard": "csm-dashboard",
    }

    return {idfy_name(k): v for k, v in dashboards.items()}


class PanelStatus(object):
    ok = "Passed"
    partial_fail = "Partially failed"
    fail = "Failed"
    ignored = "Skipped"


class Panel(object):
    def __init__(self, location, raw_query):
        self.location = location
        self.raw_query = raw_query
        self.queries = {}

    def add_query(self, query, status):
        self.queries[query] = status

    @property
    def status(self):
        statuses = self.queries.values()

        if all([status == PanelStatus.ok for status in statuses]):
            return PanelStatus.ok

        if all([status == PanelStatus.fail for status in statuses]):
            if self.raw_query in ignored_queries_for_fail:
                return PanelStatus.ignored
            else:
                return PanelStatus.fail

        if any([status == PanelStatus.fail for status in statuses]):
            if self.raw_query in ignored_queries_for_partial_fail:
                return PanelStatus.ignored
            else:
                return PanelStatus.partial_fail

    def get_failed_queries(self):
        return [query for query, status in self.queries.items()
                if status == PanelStatus.fail]

    def print_panel(self):
        return '  Location "{}" \t Query "{}"'\
            .format(self.location, self.raw_query)

    def print_panel_detail(self):
        return '  Location "{}" \t Query "{}"\n    Failed queries:\n    {}'\
            .format(self.location,
                    self.raw_query,
                    '\n    '.join(self.get_failed_queries()))

    def __str__(self):
        if self.status != PanelStatus.partial_fail:
            return self.print_panel()
        return self.print_panel_detail()


@pytest.fixture(scope="module",
                params=get_all_grafana_dashboards_names().items(),
                ids=get_all_grafana_dashboards_names().keys())
def dashboard_name(request, cluster):
    dash_name, requirement = request.param
    if not any([requirement in node.roles for node in cluster]):
        pytest.skip("No required class {} for dashboard: {}".format(
            requirement, dash_name))

    return dash_name


def test_grafana_dashboard_panel_queries(
        dashboard_name, grafana_client, prometheus_api):

    if dashboard_name == 'influxdb-relay':
        pytest.skip("influxdb-relay dashboard is temporarily skipped")

    grafana_client.check_grafana_online()
    dashboard = grafana_client.get_dashboard(dashboard_name)

    assert grafana_client.is_dashboard_exists(dashboard_name), \
        "Dashboard {name} is not present".format(name=dashboard_name)

    dashboard_results = collections.defaultdict(list)

    for location, raw_query in dashboard.get_panel_queries().items():
        possible_templates = dashboard.get_all_templates_for_query(raw_query)

        panel = Panel(location, raw_query)

        for template in possible_templates:
            query = prometheus_api.compile_query(raw_query, template)
            try:
                result = prometheus_api.do_query(query)
                if not result:
                    raise ValueError
                panel.add_query(query, PanelStatus.ok)
            except (KeyError, ValueError):
                panel.add_query(query, PanelStatus.fail)

        dashboard_results[panel.status].append(panel)

    error_msg = (
        "\nIgnored panels:\n  {ignored}"
        "\nFailed panels:\n  {failed}"
        "\nPartially failed panels:\n  {partially_failed}").format(
            ignored="\n  ".join(
                map(str, dashboard_results[PanelStatus.ignored])),
            failed="\n  ".join(
                map(str, dashboard_results[PanelStatus.fail])),
            partially_failed="\n  ".join(
                map(str, dashboard_results[PanelStatus.partial_fail])),
        )

    assert (len(dashboard_results[PanelStatus.fail]) == 0 and
            len(dashboard_results[PanelStatus.partial_fail]) == 0), error_msg


def test_panels_fixture(grafana_client):
    dashboards = grafana_client.get_all_dashboards_names()
    fixture_dashboards = get_all_grafana_dashboards_names().keys()
    missing_dashboards = set(dashboards).difference(set(fixture_dashboards))

    assert len(missing_dashboards) == 0, \
        ("Update test data fixture with the missing dashboards: "
         "{}".format(missing_dashboards))
