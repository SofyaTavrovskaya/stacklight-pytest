try:
    import salt.client
except ImportError:
    pass
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

    def cmd (self, tgt, fun, param=None, expr_form='pcre', tgt_type=None, timeout=1):
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
