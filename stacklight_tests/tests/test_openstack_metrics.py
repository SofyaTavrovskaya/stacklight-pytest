import logging
import pytest
import re
import time

from stacklight_tests import file_cache
from stacklight_tests import settings
from stacklight_tests import utils

logger = logging.getLogger(__name__)


class TestOpenstackMetrics(object):
    @pytest.mark.run(order=2)
    def test_glance_metrics(self, destructive, prometheus_api, os_clients):
        image_name = utils.rand_name("image-")
        client = os_clients.image

        logger.info("Creating a test image")
        image = client.images.create(
            name=image_name,
            container_format="bare",
            disk_format="raw",
            visibility="public")
        client.images.upload(image.id, "dummy_data")
        destructive.append(lambda: client.images.delete(image.id))
        utils.wait_for_resource_status(client.images, image.id, "active")

        logger.info("Checking the glance metrics")
        filter = {"visibility": "public"}
        images_count = len([im for im in client.images.list(
                            filters=filter)])
        images_size = sum([im["size"] for im in client.images.list(
                           filters=filter)])

        count_query = ('{__name__="openstack_glance_images",'
                       'visibility="public",status="active"}')
        err_count_msg = "Incorrect image count in metric {}".format(
            count_query)
        prometheus_api.check_metric_values(
            count_query, images_count, err_count_msg)

        size_query = ('{__name__="openstack_glance_images_size",'
                      'visibility="public", status="active"}')
        error_size_msg = "Incorrect image size in metric {}".format(size_query)
        prometheus_api.check_metric_values(
            size_query, images_size, error_size_msg)

        logger.info("Removing the test image")
        client.images.delete(image.id)
        utils.wait(
            lambda: (image.id not in [i["id"] for i in client.images.list()])
        )

    @pytest.mark.run(order=2)
    def test_keystone_metrics(self, prometheus_api, os_clients):
        client = os_clients.auth
        tenants = client.projects.list()
        users = client.users.list()

        metric_dict = {
            '{__name__="openstack_keystone_tenants_total"}':
                [len(tenants), "Incorrect tenant count in metric {}"],

            'openstack_keystone_tenants{state="enabled"}':
                [len(filter(lambda x: x.enabled, tenants)),
                 "Incorrect enabled tenant count in metric {}"],

            'openstack_keystone_tenants{state="disabled"}':
                [len(filter(lambda x: not x.enabled, tenants)),
                 "Incorrect disabled tenant count in metric {}"],

            '{__name__="openstack_keystone_roles_roles"}':
                [len(client.roles.list()),
                 "Incorrect roles count in metric {}"],

            '{__name__="openstack_keystone_users_total"}':
                [len(users), "Incorrect user count in metric {}"],

            'openstack_keystone_users{state="enabled"}':
                [len(filter(lambda x: x.enabled, users)),
                 "Incorrect enabled user count in metric {}"],

            'openstack_keystone_users{state="disabled"}':
                [len(filter(lambda x: not x.enabled, users)),
                 "Incorrect disabled user count in metric {}"]
        }

        for metric in metric_dict.keys():
            prometheus_api.check_metric_values(
                metric, metric_dict[metric][0],
                metric_dict[metric][1].format(metric))

    @pytest.mark.run(order=2)
    def test_neutron_metrics(self, prometheus_api, os_clients):
        client = os_clients.network

        metric_dict = {
            '{__name__="openstack_neutron_networks_total"}':
                [len(client.list_networks()["networks"]),
                 "Incorrect net count in metric {}"],
            '{__name__="openstack_neutron_subnets_total"}':
                [len(client.list_subnets()["subnets"]),
                 "Incorrect subnet count in metric {}"],
            '{__name__="openstack_neutron_floatingips_total"}':
                [len(client.list_floatingips()["floatingips"]),
                 "Incorrect floating ip count in metric {}"],
            '{__name__="openstack_neutron_routers_total"}':
                [len(client.list_routers()["routers"]),
                 "Incorrect router count in metric {}"],
            'openstack_neutron_routers{state="active"}':
                [len(filter(lambda x: x["status"] == "ACTIVE",
                            client.list_routers()["routers"])),
                 "Incorrect active router count in metric {}"],
            '{__name__="openstack_neutron_ports_total"}':
                [len(client.list_ports()["ports"]),
                 "Incorrect port count in metric {}"]
        }

        for metric in metric_dict.keys():
            prometheus_api.check_metric_values(
                metric, metric_dict[metric][0],
                metric_dict[metric][1].format(metric))

    @pytest.mark.run(order=2)
    def test_cinder_metrics(self, destructive, prometheus_api, os_clients):
        volume_name = utils.rand_name("volume-")
        expected_volume_status = settings.VOLUME_STATUS
        client = os_clients.volume

        logger.info("Creating a test volume")
        volume = client.volumes.create(size=1, name=volume_name)
        destructive.append(lambda: client.volumes.delete(volume))
        utils.wait_for_resource_status(client.volumes, volume.id,
                                       expected_volume_status)

        logger.info("Checking the cinder metrics")
        filter = {'status': expected_volume_status, 'all_tenants': 1}
        volumes_count = len([vol for vol in client.volumes.list(
                             search_opts=filter)])
        volumes_size = sum([vol.size for vol in client.volumes.list(
                            search_opts=filter)]) * 1024**3

        count_query = ('{{__name__="openstack_cinder_volumes",'
                       'status="{0}"}}'.format(expected_volume_status))
        err_count_msg = "Incorrect volume count in metric {}".format(
            count_query)
        prometheus_api.check_metric_values(
            count_query, volumes_count, err_count_msg)

        size_query = ('{{__name__="openstack_cinder_volumes_size",'
                      'status="{0}"}}'.format(expected_volume_status))
        error_size_msg = "Incorrect volume size in metric {}".format(
            size_query)
        prometheus_api.check_metric_values(
            size_query, volumes_size, error_size_msg)

        logger.info("Removing the test volume")
        client.volumes.delete(volume)
        utils.wait(
            lambda: (volume.id not in [v.id for v in client.volumes.list()])
        )

    @pytest.mark.run(order=2)
    def test_nova_telegraf_metrics(self, prometheus_api, os_clients):
        client = os_clients.compute

        def get_servers_count(st):
            return len(filter(
                lambda x: x.status == st, client.servers.list()))

        err_msg = "Incorrect servers count in metric {}"
        for status in ["active", "error"]:
            q = 'openstack_nova_instances{' + 'state="{}"'.format(
                status) + '}'
            prometheus_api.check_metric_values(
                q, get_servers_count(status.upper()), err_msg.format(q))

    @pytest.mark.run(order=2)
    def test_nova_services_metrics(self, prometheus_api, salt_actions):
        controllers = salt_actions.ping(
            "nova:controller:enabled:True", tgt_type="pillar", short=True)
        computes = salt_actions.ping(
            "nova:compute:enabled:True", tgt_type="pillar", short=True)
        controller_services = ["nova-conductor", "nova-consoleauth",
                               "nova-scheduler"]
        compute_services = ["nova-compute"]
        err_service_msg = "Service {} is down on the {} node"
        for controller in controllers:
            for service in controller_services:
                q = 'hostname="{}",service="{}"'.format(controller, service)
                prometheus_api.check_metric_values(
                    'openstack_nova_service{' + q + '}',
                    0,
                    err_service_msg.format(service, controller))
        for compute in computes:
            for service in compute_services:
                q = 'hostname="{}",service="{}"'.format(compute, service)
                prometheus_api.check_metric_values(
                    'openstack_nova_service{' + q + '}',
                    0, err_service_msg.format(service, compute))

    @pytest.mark.run(order=2)
    def test_http_response_metrics(self, prometheus_api, salt_actions):
        grain = 'telegraf:agent:input:http_response'
        nodes = salt_actions.ping(grain, tgt_type='grain')
        metrics = prometheus_api.get_query('http_response_status')
        logger.info("http_response_status metric list:")
        for metric in metrics:
            logger.info(
                "Service: {:<25} Value: {} Host: {}".format(
                    metric['metric']['name'],
                    metric['value'],
                    metric['metric']['host']
                )
            )

        target_dict = {}
        for node in nodes:
            target_dict[node] = salt_actions.get_grains(
                node, grain).values()[0].keys()
        logger.info("\nGot the following dict to check:\n{}\n".format(
            target_dict))

        for node in target_dict.keys():
            host = node.split(".")[0]
            for service in target_dict[node]:
                q = 'http_response_status{{name="{}", host="{}"}}'.format(
                    service, host)
                output = prometheus_api.get_query(q)
                logger.info("Waiting to get metric {}".format(q))
                msg = "Metric {} not found".format(q)
                assert len(output) != 0, msg
                prometheus_api.check_metric_values(q, 1)

    @pytest.mark.run(order=1)
    def test_openstack_api_check_status_metrics(self, prometheus_api,
                                                salt_actions):
        nodes = salt_actions.ping("I@nova:controller")
        if not nodes:
            pytest.skip("Openstack is not installed in the cluster")
        metrics = prometheus_api.get_query('openstack_api_check_status')
        logger.info("openstack_api_check_status metrics list:")
        for metric in metrics:
            logger.info("Service: {:<25} Value: {}".format(
                metric['metric']['name'], metric['value']))

        msg = 'There are no openstack_api_check_status metrics'
        assert len(metrics) != 0, msg
        # TODO(vgusev): Refactor test after changes in telegraf are done
        allowed_values = ['1', '2']
        # '2' is allowed value because some services are not present in
        # hardcoded list in telegraf. Remove after changes in telegraf are done

        for metric in metrics:
            logger.info("Check allowed values {} for service {}".format(
                ' or '.join(allowed_values), metric['metric']['name']))
            msg = 'Incorrect value in metric {}'.format(metric)
            assert any(x in allowed_values for x in metric['value']), msg

    @pytest.mark.run(order=2)
    def test_libvirt_metrics(self, prometheus_api, salt_actions, os_clients,
                             os_actions, destructive):
        def wait_for_metrics(inst_id):
            def _get_current_value(q):
                output = prometheus_api.get_query(q)
                logger.info("Got {} libvirt metrics".format(len(output)))
                return output
            query = '{{__name__=~"^libvirt.*", instance_uuid="{}"}}'.format(
                inst_id)
            output = []
            for i in xrange(5):
                output = _get_current_value(query)
                if len(output) != 0:
                    return output
                time.sleep(5)
            return output

        nodes = salt_actions.ping("I@nova:controller")
        if not nodes:
            pytest.skip("Openstack is not installed in the cluster")
        client = os_clients.compute

        logger.info("Creating a test image")
        image = os_clients.image.images.create(
            name="TestVM",
            disk_format='qcow2',
            container_format='bare')
        with file_cache.get_file(settings.CIRROS_QCOW2_URL) as f:
            os_clients.image.images.upload(image.id, f)
        destructive.append(lambda: os_clients.image.images.delete(image.id))

        logger.info("Creating a test flavor")
        flavor = os_actions.create_flavor(
            name="test_flavor", ram='64')
        destructive.append(lambda: client.flavors.delete(flavor))

        logger.info("Creating test network and subnet")
        project_id = os_clients.auth.projects.find(name='admin').id
        net = os_actions.create_network(project_id)
        subnet = os_actions.create_subnet(net, project_id, "192.168.100.0/24")

        logger.info("Creating a test instance")
        server = os_actions.create_basic_server(image, flavor, net)
        destructive.append(lambda: client.servers.delete(server))
        destructive.append(lambda: os_clients.network.delete_subnet(
            subnet['id']))
        destructive.append(lambda: os_clients.network.delete_network(
            net['id']))
        utils.wait_for_resource_status(client.servers, server, 'ACTIVE')
        logger.info("Created an instance with id {}".format(server.id))

        logger.info("Checking libvirt metrics for the instance")
        metrics = wait_for_metrics(server.id)
        metric_names = list(set([m['metric']['__name__'] for m in metrics]))
        logger.info("Got the following list of libvirt metrics: \n{}".format(
            metric_names))

        regexes = ['libvirt_domain_block_stats_read*',
                   'libvirt_domain_block_stats_write*',
                   'libvirt_domain_interface_stats_receive*',
                   'libvirt_domain_interface_stats_transmit*',
                   'libvirt_domain_info*']
        for regex in regexes:
            regex = re.compile(r'{}'.format(regex))
            logger.info("Check metrics with mask {}".format(regex.pattern))
            found = filter(regex.search, metric_names)
            logger.info("Found {} metrics for mask {}".format(
                found, regex.pattern))
            msg = "Metrics with mask '{}' not found in list {}".format(
                regex.pattern, metric_names)
            assert found, msg

        logger.info("Removing the test instance")
        client.servers.delete(server)
        utils.wait(
            lambda: (server.id not in [s.id for s in client.servers.list()])
        )

        logger.info("Removing the test network and subnet")
        os_clients.network.delete_subnet(subnet['id'])
        os_clients.network.delete_network(net['id'])

        logger.info("Removing the test image")
        os_clients.image.images.delete(image.id)

        logger.info("Removing the test flavor")
        client.flavors.delete(flavor)
