import socket

import yaml
from pprint import pprint
from clients import salt_api

import settings
import os
import utils
from io import StringIO


class LOG(object):
    @staticmethod
    def info(msg):
        pprint(msg)


class NoApplication(Exception):
    pass


class MKConfig(object):
    def __init__(self, cluster_name=None):

        if cluster_name is None:
            cluster_name = socket.getfqdn().split('.', 1)[-1]
            LOG.info("No domain/cluster_name passed, use generated: {}"
                     .format(cluster_name))
        salt = salt_api.SaltApi()
        inv = salt.salt_api.cmd(
            'salt:master', 'cmd.run', ['reclass --inventory'],
            expr_form='pillar').values()
        file_like_io = StringIO(''.join(inv).decode("utf-8"))
        inventory = yaml.load(file_like_io)

        LOG.info("Try to load nodes for domain {}".format(cluster_name))
        if "skipped_nodes" in os.environ:
            skipped_nodes = os.environ['skipped_nodes']
            self.nodes = {k: v for k, v in inventory["nodes"].items()
                          if k not in skipped_nodes}
        else:
            self.nodes = {k: v for k, v in inventory["nodes"].items()}
        LOG.info("Load nodes: {}".format(self.nodes.keys()))

    def get_application_node(self, applications):
        if isinstance(applications, basestring):
            applications = [applications]
        for fqdn, node in self.nodes.items():
            # LOG.info("Check application {} for node {}".
            #          format(application, fqdn))
            if all(app in node["applications"] for app in applications):
                LOG.info("Found applications {} for node {}".
                         format(applications, fqdn))
                return node
        raise NoApplication()

    def generate_nodes_config(self):
        nodes_config = []
        private_key = ''

        def parse_roles_from_classes(node):
            roles_mapping = {
                "openstack.control": "controller",
                "openstack.compute": "compute",
                "stacklight.server": "monitoring",
                "galera.master": "galera.master",
                "galera.slave": "galera.slave",
                "kubernetes.control": "k8s_controller",
                "kubernetes.compute": "k8s_compute",
                "grafana.client": "grafana_client",
                "kibana.server": "elasticsearch_server",
                "prometheus.server": "prometheus_server",
                "prometheus.alerta": "alerta",
            }
            cls_based_roles = [
                role for role_name, role in roles_mapping.items()
                if any(role_name in c for c in node["classes"])
            ]
            # Avoid simultaneous existence of k8s_controller
            # and k8s_compute roles
            if ("k8s_compute" in cls_based_roles and
                    "k8s_controller" in cls_based_roles):
                cls_based_roles.remove("k8s_compute")
            return cls_based_roles

        for current_node in self.nodes.values():
            node_params = current_node["parameters"]
            roles = current_node["applications"]
            roles.extend(parse_roles_from_classes(current_node))
            roles.extend(current_node["classes"])
            roles.sort()
            nodes_config.append({
                "address": node_params['_param']['single_address'],
                "hostname": node_params['linux']['network']['fqdn'],
                "username": "root",
                "private_key": private_key,
                "roles": roles,
            })

        return nodes_config

    def generate_influxdb_config(self):
        _param = self.get_application_node("influxdb")['parameters']['_param']
        return {
            "influxdb_vip":
                _param.get('grafana_influxdb_host') or
                _param['stacklight_monitor_address'],
            "influxdb_port":
                _param['influxdb_port'] or 8086,
            "influxdb_username":
                _param.get('prometheus_influxdb_username') or "lma",
            "influxdb_password":
                _param.get('prometheus_influxdb_password') or "lmapass",
            "influxdb_db_name":
                _param.get('prometheus_influxdb_db') or "prometheus",
            "influxdb_admin_password":
                _param.get('influxdb_admin_password') or "password",
        }

    def generate_elasticsearch_config(self):
        _param = (
            self.get_application_node("elasticsearch_server")['parameters'])
        _kibana_param = _param['kibana']['server']
        return {
            "elasticsearch_vip": _param['_param']['kibana_elasticsearch_host'],
            "elasticsearch_port": _kibana_param['database']['port'],
            "kibana_port": _kibana_param['bind']['port'],
        }

    def generate_grafana_config(self):
        _param = self.get_application_node("grafana_client")['parameters']
        _client_param = _param['grafana']['client']
        return {
            "grafana_vip": _client_param['server']['host'],
            "grafana_port": _client_param['server']['port'],
            "grafana_username": _client_param['server']['user'],
            "grafana_password": _client_param['server']['password'],
            "grafana_default_datasource": _client_param['datasource'].keys()[0]
        }

    def generate_keystone_config(self):
        _param = (
            self.get_application_node("keystone")['parameters']['keystone'])
        return {
            "admin_name": _param['server']['admin_name'],
            "admin_password": _param['server']['admin_password'],
            "admin_tenant": _param['server']['admin_tenant'],
            "private_address": _param['server']['bind']['private_address'],
            "public_address": _param['server']['bind']['public_address'],
        }

    def generate_mysql_config(self):
        _param = self.get_application_node("galera")['parameters']['_param']
        return {
            "mysql_user": _param['mysql_admin_user'],
            "mysql_password": _param['mysql_admin_password']
        }

    def generate_prometheus_config(self):
        def get_port(input_line):
            return input_line["ports"][0].split(":")[0]

        _param = self.get_application_node(
            ["prometheus_server", "service.docker.client"])['parameters']
        expose_params = (
            _param["docker"]["client"]["stack"]["monitoring"]["service"])

        return {
            "use_prometheus_query_alert": True,
            "prometheus_vip": _param["_param"]["prometheus_control_address"],
            "prometheus_server_port":
                get_port(expose_params["server"]),
            "prometheus_alertmanager":
                get_port(expose_params["alertmanager"]),
            "prometheus_pushgateway":
                get_port(expose_params["pushgateway"]),
        }

    def generate_alerta_config(self):
        def get_port(input_line):
            return input_line["ports"][0].split(":")[0]
        _param = self.get_application_node(
            ["alerta", "service.docker.client"])['parameters']
        expose_params = (
            _param["docker"]["client"]["stack"]["monitoring"]["service"])

        return {
            "alerta_host": _param["_param"]["prometheus_control_address"],
            "alerta_port":
                get_port(expose_params["alerta"]),
            "alerta_username": _param["_param"]["alerta_admin_username"]
        }

    def main(self):
        config = {
            "env": {"type": "mk"},
        }
        for application in settings.CONFIGURE_APPS:
            try:
                method = getattr(self, "generate_{}_config".
                                 format(application))
                config.update({
                    application: method()
                })
                LOG.info("INFO: {} configured".format(application))
            except NoApplication:
                LOG.info("INFO: No {} installed, skip".format(application))

        config_filename = utils.get_fixture("config.yaml",
                                            check_existence=False)
        LOG.info("INFO: Saving config to {}".format(config_filename))
        with open(config_filename, "w") as f:
            yaml.safe_dump(config, f, default_flow_style=False)


def main():
    MKConfig(cluster_name=settings.ENV_CLUSTER_NAME).main()


if __name__ == '__main__':
    main()
