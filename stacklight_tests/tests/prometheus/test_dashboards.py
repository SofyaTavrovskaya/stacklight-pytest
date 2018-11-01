import collections

import pytest


ignored_queries_for_fail = [
    # Cinder. Default installation does not contain cinder-volume
    'max(openstack_cinder_services{state="down", service="cinder-volume"})',
    'max(openstack_cinder_services{service="cinder-volume"}) by (state)',
    'max(openstack_cinder_services'
    '{state="disabled", service="cinder-volume"})',
    'max(openstack_cinder_services{state="up", service="cinder-volume"})',

    # Heat. By default metric is not present if no tracked value
    'irate(openstack_heat_http_response_times_count{http_status="5xx"}[5m])',

    # Partial Elasticsearch metric PROD-19161
    'quantile_over_time(0.9, elasticsearch_indices_flush_total_latency'
    '{host="$host"}[5m])',

    # Openstack. We can have situation without 5xx errors
    'sum(rate(openstack_http_response_times_count{http_status=~"5.."}'
    '[$rate_interval])) by (service)',

    # Cinder. We can have only enabled/up cinder services
    'max(count(openstack_cinder_service_state{binary="cinder-volume"} == 0 '
    'and openstack_cinder_service_status{binary="cinder-volume"} == 0) '
    'by (instance))',
    'max(count(openstack_cinder_service_state{binary="cinder-volume"} == 0 '
    'and openstack_cinder_service_status{binary="cinder-volume"} == 1) '
    'by (instance))',
    'max(count(openstack_cinder_service_state{binary="cinder-volume"} == 1 '
    'and openstack_cinder_service_status{binary="cinder-volume"} == 0) '
    'by (instance))',
    'max(count(openstack_cinder_service_state{binary="cinder-scheduler"} == 1 '
    'and openstack_cinder_service_status{binary="cinder-scheduler"} == 0) '
    'by (instance))',
    'max(count(openstack_cinder_service_state{binary="cinder-scheduler"} == 0 '
    'and openstack_cinder_service_status{binary="cinder-scheduler"} == 1) '
    'by (instance))',
    'max(count(openstack_cinder_service_state{binary="cinder-scheduler"} == 0 '
    'and openstack_cinder_service_status{binary="cinder-scheduler"} == 0) '
    'by (instance))',

    # Skip 0 as query, that is just visual line
    '0',

    # Haproxy. We can have installation without SSL on haproxy
    'max(haproxy_server_ssl_connections {host=~"$host"}) without(pid) > 0',

    # Influxdb. We can have no stopped instances of influxdb
    'count(influxdb_up == 0)',

    # Keepalived. Keepalived_state metric appears only after changing of status
    'keepalived_state{host="$host"}',
    'keepalived_state{host=~"$host"}',

    # Prometheus. Skip 1.x prometheus metric
    'prometheus_local_storage_target_heap_size_bytes'
    '{instance=~"$instance:[1-9][0-9]*"}',

    # Neutron. We can have only up and enabled agents
    'max(count(openstack_neutron_agent_state{binary="neutron-metadata-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-metadata-agent"} '
    '== 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-metadata-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-metadata-agent"} '
    '== 1) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-metadata-agent"} '
    '== 1 and openstack_neutron_agent_status{binary="neutron-metadata-agent"} '
    '== 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-openvswitch-'
    'agent"} == 1 and openstack_neutron_agent_status{binary="neutron-'
    'openvswitch-agent"} == 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-openvswitch-'
    'agent"} == 0 and openstack_neutron_agent_status{binary="neutron-'
    'openvswitch-agent"} == 1) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-openvswitch-'
    'agent"} == 0 and openstack_neutron_agent_status{binary="neutron-'
    'openvswitch-agent"} == 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-l3-agent"} '
    '== 1 and openstack_neutron_agent_status{binary="neutron-l3-agent"} '
    '== 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-l3-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-l3-agent"} '
    '== 1) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-l3-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-l3-agent"} '
    '== 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-dhcp-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-dhcp-agent"} '
    '== 0) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-dhcp-agent"} '
    '== 0 and openstack_neutron_agent_status{binary="neutron-dhcp-agent"} '
    '== 1) by (instance))',
    'max(count(openstack_neutron_agent_state{binary="neutron-dhcp-agent"} '
    '== 1 and openstack_neutron_agent_status{binary="neutron-dhcp-agent"} '
    '== 0) by (instance))',

    # Neutron. Right after deployment we have no lbaases and instances
    'max(sum(openstack_neutron_ports{owner=~"compute:.*"}) by '
    '(instance,state)) by (state)',
    'max(openstack_neutron_lbaas_loadbalancers) by (status)',

    # Nova. We can have only up and enabled nova services
    'max(count(openstack_nova_service_state{service="nova-compute"} == 0 '
    'and openstack_nova_service_status{service="nova-compute"} == 1) by '
    '(instance))',
    'max(count(openstack_nova_service_state{service="nova-compute"} == 1 '
    'and openstack_nova_service_status{service="nova-compute"} == 0) by '
    '(instance))',
    'max(count(openstack_nova_service_state{service="nova-compute"} == 0 '
    'and openstack_nova_service_status{service="nova-compute"} == 0) by '
    '(instance))',

    'max(count(openstack_nova_service_state{binary="nova-scheduler"} == 0 '
    'and openstack_nova_service_status{binary="nova-scheduler"} == 1) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-scheduler"} == 1 '
    'and openstack_nova_service_status{binary="nova-scheduler"} == 0) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-scheduler"} == 0 '
    'and openstack_nova_service_status{binary="nova-scheduler"} == 0) by '
    '(instance))',

    'max(count(openstack_nova_service_state{binary="nova-consoleauth"} == 1 '
    'and openstack_nova_service_status{binary="nova-consoleauth"} == 0) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-consoleauth"} == 0 '
    'and openstack_nova_service_status{binary="nova-consoleauth"} == 1) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-consoleauth"} == 0 '
    'and openstack_nova_service_status{binary="nova-consoleauth"} == 0) by '
    '(instance))',

    'max(count(openstack_nova_service_state{binary="nova-conductor"} == 0 '
    'and openstack_nova_service_status{binary="nova-conductor"} == 1) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-conductor"} == 1 '
    'and openstack_nova_service_status{binary="nova-conductor"} == 0) by '
    '(instance))',
    'max(count(openstack_nova_service_state{binary="nova-conductor"} == 0 '
    'and openstack_nova_service_status{binary="nova-conductor"} == 0) by '
    '(instance))',

    # Kubernetes. We have no rkt containers by default
    'sum(rate(container_network_transmit_bytes_total{rkt_container_name!="",'
    'kubernetes_io_hostname=~"^$host$"}[$rate_interval])) by '
    '(kubernetes_io_hostname, rkt_container_name)',
    'sum(rate(container_network_transmit_bytes_total{rkt_container_name!="",'
    'kubernetes_io_hostname=~"^$host$"}[$rate_interval])) by '
    '(kubernetes_io_hostname, rkt_container_name)',
    'sum(rate(container_cpu_usage_seconds_total{rkt_container_name!="",'
    'kubernetes_io_hostname=~"^$host$"}[$rate_interval])) by '
    '(kubernetes_io_hostname, rkt_container_name)',
    'sum(container_memory_working_set_bytes{rkt_container_name!="",'
    'kubernetes_io_hostname=~"^$host$"}) by '
    '(kubernetes_io_hostname, rkt_container_name)',

    # Haproxy. We can have no failed backends
    'avg(sum(haproxy_active_servers{type="server"}) by (host, proxy) + '
    'sum(haproxy_backup_servers{type="server"}) by (host, proxy)) by (proxy) '
    '- avg(sum(haproxy_active_servers{type="backend"}) by (host, proxy) '
    '+ sum(haproxy_backup_servers{type="backend"}) by (host, proxy)) '
    'by (proxy) > 0',
]


ignored_queries_for_partial_fail = [
    # Haproxy connections are not present on all nodes
    'max(haproxy_server_ssl_connections {host=~"$host"}) without(pid) > 0',
    'max(haproxy_server_connections {host=~"$host"}) without(pid) > 0',

    # Values coming only from two nodes PROD-19161
    'max(elasticsearch_indices_search_fetch_latency{host="$host"}',
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
        "Nova Hypervisor Overview": "service.nova.compute.kvm",
        "Heat": "heat",
        "InfluxDB": "influxdb",
        "InfluxDB Relay": "influxdb",
        "Jenkins": "system.jenkins.client",
        "Keepalived": "keepalived",
        "Keystone": "keystone",
        "Kibana": "kibana",
        "Kubernetes cluster monitoring": "kubernetes",
        "Memcached": "memcached",
        "MySQL": "galera.master",
        "Neutron": "service.neutron.control.cluster",
        "Nova Overview": "nova",
        "Nova Instances": "nova",
        "Nova Utilization": "nova",
        "Openstack overview": "nova",
        "Openstack tenants": "nova",
        "Octavia": "octavia",
        "Ntp": "linux",
        "Nginx": "nginx",
        "OpenContrail Controller": "opencontrail",
        "OpenContrail vRouter": "opencontrail",
        "Prometheus Performances": "prometheus",
        "Prometheus Stats": "prometheus",
        "RabbitMQ": "rabbitmq",
        # System dasboard was divided into three, skip:
        # "System": "linux",
        "System Overview": "linux",
        "System Networking": "linux",
        "System Disk I O": "linux",
        "Remote storage adapter": "prometheus.remote_storage_adapter",
        "Grafana": "grafana",
        "Alertmanager": "prometheus",
        "Zookeeper": "opencontrail",
        "Pushgateway": "prometheus",
        "Prometheus Relay": "prometheus.relay",
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
        "\nPassed panels:\n  {passed}"
        "\nIgnored panels:\n  {ignored}"
        "\nFailed panels:\n  {failed}"
        "\nPartially failed panels:\n  {partially_failed}").format(
            passed="\n  ".join(
                map(str, dashboard_results[PanelStatus.ok])),
            ignored="\n  ".join(
                map(str, dashboard_results[PanelStatus.ignored])),
            failed="\n  ".join(
                map(str, dashboard_results[PanelStatus.fail])),
            partially_failed="\n  ".join(
                map(str, dashboard_results[PanelStatus.partial_fail])))

    assert (len(dashboard_results[PanelStatus.fail]) == 0 and
            len(dashboard_results[PanelStatus.partial_fail]) == 0), error_msg


def test_panels_fixture(grafana_client):
    dashboards = grafana_client.get_all_dashboards_names()
    # Workaround for Main dashboard
    dashboards.remove("main")
    fixture_dashboards = get_all_grafana_dashboards_names().keys()
    missing_dashboards = set(dashboards).difference(set(fixture_dashboards))

    assert len(missing_dashboards) == 0, \
        ("Update test data fixture with the missing dashboards: "
         "{}".format(missing_dashboards))


def test_grafana_database_type(salt_actions):
    db_type = salt_actions.get_pillar_item(
        "I@grafana:client",
        "docker:client:stack:"
        "dashboard:service:grafana:"
        "environment:GF_DATABASE_TYPE")[0]

    assert db_type == "mysql"
