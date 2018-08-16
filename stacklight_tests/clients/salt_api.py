import salt.client


class SaltApi(object):
    def __init__(self):
        self.salt_api = salt.client.LocalClient()

    def run_cmd(self, tgt, command, tgt_type='compound'):
        return self.salt_api.cmd(
            tgt, "cmd.run", [command], tgt_type=tgt_type).values()

    def ping(self, tgt='*', timeout=3, tgt_type='compound'):
        nodes = self.salt_api.cmd(tgt, "test.ping", timeout=timeout,
                                  tgt_type=tgt_type).keys()
        return nodes

    def get_pillar(self, tgt, pillar, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar], tgt_type=tgt_type)
        return result

    def get_pillar_item(self, tgt, pillar_item, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar_item], tgt_type=tgt_type).values()
        return [i for i in result if i]

    def get_grains(self, tgt, grains, tgt_type='compound'):
        result = self.salt_api.cmd(
            tgt, 'grains.get', [grains], tgt_type=tgt_type)
        return result

    def service_status(self, tgt, service):
        return self.salt_api.cmd(tgt, "service.status", [service])

    def check_service_installed(self, name, tgt, tgt_type='compound'):
        """Checks that service is installed on nodes with provided role."""
        nodes = self.ping(tgt, tgt_type=tgt_type)
        for node in nodes:
            output = self.run_cmd(node, "dpkg-query -l {}".format(name))
            err = "Package {} is not installed on the {} node"
            assert "no packages found" not in output[0], err.format(
                name, node)

    def check_service_running(self, name, tgt, tgt_type='compound'):
        """Checks that service is running on nodes with provided role."""
        nodes = self.ping(tgt, tgt_type=tgt_type)
        for node in nodes:
            err = "Service {} is stopped on the {} node"
            assert self.service_status(node, name).values()[0], err.format(
                name, node)
