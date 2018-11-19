import logging
import pytest

from stacklight_tests import settings
from stacklight_tests import utils
from stacklight_tests.tests.test_functional import wait_for_resource_status

logger = logging.getLogger(__name__)


class TestOpenstackMetrics(object):
    @pytest.mark.run(order=1)
    def test_glance_metrics(self, destructive, prometheus_api, os_clients):
        image_name = utils.rand_name("image-")
        client = os_clients.image
        image = client.images.create(
            name=image_name,
            container_format="bare",
            disk_format="raw",
            visibility="public")
        client.images.upload(image.id, "dummy_data")
        wait_for_resource_status(client.images, image.id, "active")
        destructive.append(lambda: client.images.delete(image.id))
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

        client.images.delete(image.id)
        utils.wait(
            lambda: (image.id not in [i["id"] for i in client.images.list()])
        )

    @pytest.mark.run(order=1)
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

    @pytest.mark.run(order=1)
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

    @pytest.mark.run(order=1)
    def test_cinder_metrics(self, destructive, prometheus_api, os_clients):
        volume_name = utils.rand_name("volume-")
        expected_volume_status = settings.VOLUME_STATUS
        client = os_clients.volume
        volume = client.volumes.create(size=1, name=volume_name)
        wait_for_resource_status(client.volumes, volume.id,
                                 expected_volume_status)
        destructive.append(lambda: client.volume.delete(volume))
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

        client.volumes.delete(volume)
        utils.wait(
            lambda: (volume.id not in [v.id for v in client.volumes.list()])
        )

    @pytest.mark.run(order=1)
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

    @pytest.mark.run(order=1)
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

    def test_http_response_metrics(self, prometheus_api, salt_actions):
        nodes = salt_actions.ping("I@nova:controller")
        if not nodes:
            pytest.skip("Openstack is not installed in the cluster")
        # TODO(vgusev): Extend test with opencontrail services
        services = salt_actions.get_grains(
            nodes[0], 'telegraf:agent:input:http_response').values()[0].keys()
        for service in services:
            for node in nodes:
                host = node.split(".")[0]
                q = 'http_response_status{{name="{}", host="{}"}}'.format(
                    service, host)
                output = prometheus_api.get_query(q)
                logger.info("Waiting to get metric {}".format(q))
                msg = "Metric {} not found".format(q)
                assert len(output) != 0, msg
                prometheus_api.check_metric_values(q, 1)

    def test_openstack_api_check_status_metrics(self, prometheus_api,
                                                salt_actions):
        nodes = salt_actions.ping("I@nova:controller")
        if not nodes:
            pytest.skip("Openstack is not installed in the cluster")
        metrics = prometheus_api.get_query('openstack_api_check_status')
        logger.info("openstack_api_check_status metrics list: {}".format(
            metrics))
        msg = 'There are no openstack_api_check_status metrics'
        assert len(metrics) != 0, msg
        # TODO(vgusev): Refactor test after changes in telegraf are done
        for metric in metrics:
            logger.info("Check value '1' for service {}".format(
                metric['metric']['name']))
            msg = 'Incorrect value in metric {}'.format(metric)
            assert '1' in metric['value'], msg
