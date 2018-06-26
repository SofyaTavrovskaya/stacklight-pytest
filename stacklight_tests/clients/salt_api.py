try:
    import salt.client
except ImportError:
    pass


class SaltApi(object):
    def __init__(self):
        self.salt_api = salt.client.LocalClient()

    def run_cmd(self, tgt, command, expr_form='compound'):
        return self.salt_api.cmd(
            tgt, "cmd.run", [command], expr_form=expr_form).values()

    def ping(self, tgt='*', timeout=3, expr_form='compound'):
        nodes = self.salt_api.cmd(tgt, "test.ping", timeout=timeout,
                                  expr_form=expr_form).keys()
        return nodes

    def get_pillar(self, tgt, pillar, expr_form='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar], expr_form=expr_form)
        return result

    def get_pillar_item(self, tgt, pillar_item, expr_form='compound'):
        result = self.salt_api.cmd(
            tgt, 'pillar.get', [pillar_item], expr_form=expr_form).values()
        return [i for i in result if i]

    def get_grains(self, tgt, grains, expr_form='compound'):
        result = self.salt_api.cmd(
            tgt, 'grains.get', [grains], expr_form=expr_form)
        return result

    def service_status(self, tgt, service):
        return self.salt_api.cmd(tgt, "service.status", [service])
