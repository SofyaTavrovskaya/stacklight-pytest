import salt.client
import os
import requests


class salt_remote:
    def __init__(self, headers, user, password, url):
            self.headers = headers
            self.user = user
            self.password = password
            self.url = url

    def get_session(self):
        login_payload = {'username': self.user,
                         'password': self.password, 'eauth': 'pam'}

        login_request = requests.post(os.path.join(self.url,
                                                   'login'),
                                      headers=self.headers, data=login_payload)
        if login_request.ok:
            self.cookies = login_request.cookies
        else:
            raise EnvironmentError("401 Not authorized.")

    def cmd(self, tgt, fun, param=None, expr_form='pcre', tgt_type=None,
            timeout=1):
        self.get_session()
        accept_key_payload = {'fun': fun, 'tgt': tgt, 'client': 'local',
                              'expr_form': expr_form, 'tgt_type': tgt_type,
                              'timeout': timeout}
        if param:
            accept_key_payload['arg'] = param
        try:
            result = requests.post(self.url, headers=self.headers,
                                   data=accept_key_payload,
                                   cookies=self.cookies)
            if result.ok:
                return result.json()['return'][0]
            else:
                raise
        except:
            raise EnvironmentError("Failed")


class SaltApi(object):
    def __init__(self):
        if "SALT_URL" in os.environ.keys():
            self.salt_api = salt_remote({'Accept': 'application/json'},
                                        os.environ['SALT_USERNAME'],
                                        os.environ['SALT_PASSWORD'],
                                        os.environ['SALT_URL'])
        else:
            self.salt_api = salt.client.LocalClient()

    def run_cmd(self, tgt, command, tgt_type='compound'):
        return self.salt_api.cmd(
            tgt, "cmd.run", [command], tgt_type=tgt_type).values()

    def ping(self, tgt='*', timeout=3, tgt_type='compound', short=False):
        nodes = self.salt_api.cmd(tgt, "test.ping", timeout=timeout,
                                  tgt_type=tgt_type).keys()
        return nodes if not short else [node.split('.')[0] for node in nodes]

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
