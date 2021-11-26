import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from fake_useragent import UserAgent

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class Service:
    def __init__(self, dict_of_parameters={}):
        assert dict_of_parameters, 'Not enough parameters for >>> parsers.shops.services.checking_page_loading!'
        self.session = dict_of_parameters['session']
        self.url = dict_of_parameters['url']
        self.title = dict_of_parameters['title']
        self.headers = dict_of_parameters.get('headers', {'User-Agent': UserAgent().random})
        self.timeout = dict_of_parameters.get('timeout', (2, 5))
        self.params = dict_of_parameters.get('params', '')
        self.method = dict_of_parameters.get('method', 'get')
        self.data = dict_of_parameters.get('data', {})
        self.enc = dict_of_parameters.get('encoding', '')

    def checking_page_loading(self):
        response = ''
        try:
            if self.method == 'get':
                response = self.session.get(url=self.url,
                                            params=self.params,
                                            headers=self.headers,
                                            verify=False,
                                            timeout=self.timeout)
            elif self.method == 'post':
                response = self.session.post(url=self.url,
                                             params=self.params,
                                             data=self.data,
                                             headers=self.headers,
                                             verify=False,
                                             timeout=self.timeout)
        except requests.exceptions.ReadTimeout:
            logger.info(f'Oops. Read timeout from <{self.title}> occurred!')
        except requests.exceptions.ConnectTimeout:
            logger.info(f'Oops. Connection timeout from <{self.title}> occurred!')
        except requests.exceptions.ConnectionError:
            logger.info(f'Oops. Connection error from <{self.title}> occurred!')
        else:
            if not self.enc:
                response.encoding = 'utf8'
        finally:
            return response
