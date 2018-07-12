import random
from stacklight_tests.clients import salt_api
import os

import stacklight_tests.custom_exceptions as exceptions
from stacklight_tests.clients.system import general_client


class Cluster(object):
    def __init__(self, hosts=None):
        """Container class for haos.objects.host.Host objects.
        :param hosts: list of haos.objects.host.Host objects
        :return: instance of Cluster
        """
        self.hosts = hosts or []

        if not all([isinstance(host, Host) for host in self.hosts]):
            raise ValueError
        if not isinstance(self.hosts, list):
            raise ValueError

    def __iter__(self):
        return iter(self.hosts)

    def __len__(self):
        return len(self.hosts)

    def __getitem__(self, index):
        return self.hosts[index]

    def __setitem__(self, index, host):
        if not isinstance(host, Host):
            raise ValueError
        self.hosts[index] = host

    def __delitem__(self, index):
        del self.hosts[index]

    def first(self):
        try:
            return self.hosts[0]
        except IndexError:
            raise exceptions.EmptyCluster

    def filter_by_role(self, role):
        return Cluster(hosts=[x for x in self.hosts if role in x.roles])

    def get_by_address(self, address):
        for host in self.hosts:
            if host.address == address:
                return host
        return exceptions.NoValidHost(
            condition="address == {0}".format(address))

    def get_by_hostname(self, hostname):
        for host in self.hosts:
            if hostname in host.hostname or host.hostname == hostname:
                return host
        raise exceptions.NoValidHost(
            condition="hostname == {0}".format(hostname))

    def add_host(self, host):
        if not isinstance(host, Host):
            raise ValueError
        self.hosts.append(host)

    def get_controllers(self):
        return self.filter_by_role("controller")

    def get_random_controller(self):
        return random.choice(self.filter_by_role("controller"))

    def get_random_compute(self):
        return random.choice(self.filter_by_role("compute"))


class Host(object):
    def __init__(self, address, roles=None, *args, **kwargs):
        if "SALT_URL" in os.environ.keys():
            self.exec_command = self.execc
            self.check_call = self.execc
            self.fqdn = kwargs.get("hostname")
        else:
            self.os = general_client.GeneralActionsClient(
                address=address,
                username=kwargs.get("username", "root"),
                password=kwargs.get("password"),
                private_key=kwargs.get("private_key"))
            self.exec_command = self.os.exec_command
            self.check_call = self.os.check_call
            self.fqdn = kwargs.get("hostname") or self.long_hostname
        self.address = address
        self.roles = roles or []

    @property
    def hostname(self):
        return self.fqdn.split('.')[0]

    @property
    def long_hostname(self):
        return self.fqdn

    def execc(self, cmd):
        salt = salt_api.SaltApi()
        return salt.run_cmd(self.fqdn, 'cmd.run', [cmd], expr_form='pcre')
