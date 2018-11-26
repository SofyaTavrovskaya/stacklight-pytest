import logging
import pytest
import os

logger = logging.getLogger(__name__)


class TestMetrics(object):
    target_metrics = {
        "cpu": ['cpu_usage_system', 'cpu_usage_softirq', 'cpu_usage_steal',
                'cpu_usage_user', 'cpu_usage_irq', 'cpu_usage_idle',
                'cpu_usage_guest_nice', 'cpu_usage_iowait', 'cpu_usage_nice',
                'cpu_usage_guest'],
        "mem": ['mem_free', 'mem_inactive', 'mem_active', 'mem_used',
                'mem_available_percent', 'mem_cached', 'mem_buffered',
                'mem_available', 'mem_total', 'mem_used_percent'],
        "system_load": ['system_load15', 'system_load1', 'system_load5'],
        "disk": ['diskio_io_time', 'diskio_reads', 'diskio_writes',
                 'disk_inodes_total', 'disk_used_percent',
                 'diskio_read_bytes', 'disk_free', 'disk_inodes_used',
                 'disk_used', 'diskio_write_time', 'diskio_write_bytes',
                 'diskio_iops_in_progress', 'disk_inodes_free',
                 'diskio_read_time', 'disk_total'],
        "swap": ['swap_free', 'swap_in', 'swap_out', 'swap_total', 'swap_used',
                 'swap_used_percent'],
        "processes": ['processes_blocked', 'processes_paging',
                      'processes_running', 'processes_sleeping',
                      'processes_stopped', 'processes_total',
                      'processes_total_threads', 'processes_unknown',
                      'processes_zombies'],
        "kernel": ['kernel_boot_time', 'kernel_context_switches',
                   'kernel_interrupts', 'kernel_processes_forked']
    }

    def test_etcd_metrics(self, salt_actions, prometheus_api):
        nodes = salt_actions.ping("services:etcd", tgt_type="grain")
        if not nodes:
            pytest.skip("Etcd is not installed in the cluster")
        expected_hostnames = [
            salt_actions.get_pillar_item(node, "etcd:server:bind:host")[0]
            for node in nodes]

        metrics = prometheus_api.get_query("etcd_server_has_leader")
        hostnames = [metric["metric"]["instance"].split(":")[0]
                     for metric in metrics]
        assert set(expected_hostnames) == set(hostnames)

    def test_telegraf_metrics(self, prometheus_api, salt_actions):
        expected_hostnames = salt_actions.ping(short=True)
        metrics = prometheus_api.get_query("system_uptime")
        hostnames = [metric["metric"]["host"] for metric in metrics]
        assert set(expected_hostnames) == set(hostnames)

    def test_prometheus_metrics(self, prometheus_api):
        metric = prometheus_api.get_query("prometheus_build_info")
        assert len(metric) != 0

    @pytest.mark.parametrize("target,metrics", target_metrics.items(),
                             ids=target_metrics.keys())
    def test_system_metrics(self, prometheus_api, salt_actions,
                            target, metrics):
        expected_hostnames = salt_actions.ping(short=True)
        for hostname in expected_hostnames:
            if "SKIP_NODES" in os.environ.keys():
                if hostname in os.environ['SKIP_NODES']:
                    print "Skip {}".format(hostname)
                    continue
            for metric in metrics:
                q = ('{}{{host="{}"}}'.format(metric, hostname))
                msg = "Metric {} not found".format(q)
                output = prometheus_api.get_query(q)
                assert len(output) != 0, msg

    def test_k8s_metrics(self, salt_actions, prometheus_api):
        nodes = salt_actions.ping("services:kubernetes", tgt_type="grain")

        if not nodes:
            pytest.skip("There are no kubernetes nodes in the cluster")

        metrics = [
            'kubernetes_build_info', 'kubernetes_node_memory_available_bytes',
            'kubernetes_pod_container_memory_rss_bytes',
            'kubernetes_system_container_rootfs_available_bytes'
        ]

        for metric in metrics:
            q = ('{{__name__=~"{}"}}'.format(metric))
            output = prometheus_api.get_query(q)
            logger.info("Waiting to get metric {}".format(metric))
            msg = "Metric {} not found".format(metric)
            assert len(output) != 0, msg

    def test_mysql_metrics(self, salt_actions):
        mysql_hosts = salt_actions.ping("services:galera", tgt_type="grain")
        expected_metrics = [
            'mysql_wsrep_connected', 'mysql_wsrep_local_cert_failures',
            'mysql_wsrep_local_commits', 'mysql_wsrep_local_send_queue',
            'mysql_wsrep_ready', 'mysql_wsrep_received',
            'mysql_wsrep_received_bytes', 'mysql_wsrep_replicated',
            'mysql_wsrep_replicated_bytes', 'mysql_wsrep_cluster_size',
            'mysql_wsrep_cluster_status', 'mysql_table_locks_immediate',
            'mysql_table_locks_waited', 'mysql_slow_queries',
            'mysql_threads_cached', 'mysql_threads_connected',
            'mysql_threads_created', 'mysql_threads_running'
        ]

        postfixes = [
            'admin_commands', 'alter_db', 'alter_table', 'begin',
            'call_procedure', 'change_db', 'check', 'commit', 'create_db',
            'create_index', 'create_procedure', 'create_table', 'create_user',
            'dealloc_sql', 'delete', 'drop_db', 'drop_index', 'drop_procedure',
            'drop_table', 'execute_sql', 'flush', 'grant', 'insert',
            'insert_select', 'prepare_sql', 'release_savepoint', 'rollback',
            'savepoint', 'select', 'set_option', 'show_collations',
            'show_create_table', 'show_databases', 'show_fields',
            'show_grants', 'show_master_status', 'show_status',
            'show_table_status', 'show_tables', 'show_variables',
            'show_warnings', 'unlock_tables', 'update'
        ]

        handlers = [
            'commit', 'delete', 'external_lock', 'prepare', 'read_first',
            'read_key', 'read_next', 'read_rnd', 'read_rnd_next', 'rollback',
            'savepoint', 'update', 'write'
        ]

        for postfix in postfixes:
            expected_metrics.append("mysql_commands_{}".format(postfix))
        for handler in handlers:
            expected_metrics.append("mysql_handler_{}".format(handler))

        for host in mysql_hosts:
            cmd = "curl -s localhost:9126/metrics | awk '/^mysql/{print $1}'"
            got_metrics = salt_actions.run_cmd(host, cmd)[0].split("\n")
            hostname = host.split(".")[0]
            for metric in expected_metrics:
                metric = (metric + '{host="' + hostname +
                          '",server="/var/run/mysqld/mysqld.sock"}')
                err_msg = ("Metric {} not found in received list of mysql "
                           "metrics on {} node".format(metric, hostname))
                assert metric in got_metrics, err_msg

    def test_prometheus_targets(self, salt_actions, prometheus_api):
        def get_replicas_count(stack, service):
            tgt = "I@docker:swarm and I@prometheus:server"
            replica = ('docker:client:stack:{}:service:{}:'
                       'deploy:replicas'.format(stack, service))
            mode = ('docker:client:stack:{}:service:{}:'
                    'deploy:mode'.format(stack, service))
            count = salt_actions.get_pillar_item(tgt, replica)
            if (not count and salt_actions.get_pillar_item(
                    tgt, mode) == ['global']):
                count = [len(salt_actions.ping(tgt))]
            return count

        target_dict = {}
        mapping = {
            'alertmanager': ['monitoring', 'alertmanager'],
            'prometheus': ['monitoring', 'server'],
            'remote_agent': ['monitoring', 'remote_agent'],
            'pushgateway': ['monitoring', 'pushgateway'],
            'grafana': ['dashboard', 'grafana']
        }
        if salt_actions.ping("I@nova:controller"):
            mapping.update(
                {'remote_agent_openstack': ['monitoring', 'remote_agent']})
        for service, pillar in mapping.items():
            target_dict[service] = get_replicas_count(pillar[0], pillar[1])[0]

        if salt_actions.ping("I@kubernetes:pool"):
            k8s_map = {
                'kubernetes-api': 'I@kubernetes:master',
                'kubernetes-node': 'I@kubernetes:pool',
                'etcd': 'I@etcd:server'
            }
            if salt_actions.ping(
                    "I@kubernetes:master:network:calico:enabled:True"):
                k8s_map.update({'calico': "I@kubernetes:pool:network:calico"})
            for service, pillar in k8s_map.items():
                target_dict[service] = len(salt_actions.ping(pillar))
        logger.info("Got the following dict to check:\n{}".format(target_dict))

        for target, count in target_dict.items():
            q = 'up{{job="{}"}}'.format(target)
            output = prometheus_api.get_query(q)
            logger.info('Got {} metrics for {} query'.format(output, q))
            msg = ('Incorrect count of metrics for {} target. '
                   'Received list {}'.format(target, output))
            assert len(output) == count, msg
            prometheus_api.check_metric_values(q, 1)

        service_dict = {
            'telegraf': 'I@telegraf:agent or I@telegraf:remote_agent',
            'fluentd': 'I@fluentd:agent',
            'prometheus_lts': 'I@prometheus:relay',
            'prometheus_relay': 'I@prometheus:relay',
            'libvirt_qemu_exporter': 'I@prometheus:exporters:libvirt',
            'jmx_cassandra_exporter': 'I@prometheus:exporters:jmx'
        }
        for service, tgt in service_dict.items():
            nodes = salt_actions.ping(tgt, short=True)
            for node in nodes:
                q = ('up{{host="{}",job="{}"}}'.format(node, service))
                output = prometheus_api.get_query(q)
                logger.info("Waiting to get metric {}".format(q))
                msg = "Metric {} not found".format(q)
                assert len(output) != 0, msg
                prometheus_api.check_metric_values(q, 1)

    def test_up_metrics(self, prometheus_api):
        q = '{__name__=~".*_up"}'
        metrics = prometheus_api.get_query(q)
        for metric in metrics:
            msg = 'Metric {} has value {}'.format(
                metric['metric']['__name__'], metric['value'])
            if metric.get('metric').get('host', ''):
                msg = msg + ' on the node {}'.format(metric['metric']['host'])
            logger.info(msg)
            err_msg = 'Incorrect value in metric {}'.format(metric)
            assert '1' in metric['value'], err_msg
