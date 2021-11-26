import logging
import bs4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from main.models import Xhr
import datetime
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
from concurrent import futures
from .services import Service

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class Adeo:

    def __init__(self, search=''):
        # загрузка параметров сессии из базы данных
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value, }
            for key in Cookie.objects.filter(title='adeopro').all()
        ]
        el = Xhr.objects.values('remember_me', 'legacyapp')
        self.remember_me = el[0]['remember_me']
        self.legacy_app = el[0]['legacyapp']
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []  # список для хранения результатов парсинга
        self.search = search

    def get_offer_list(self):
        """Возвращает HTML-код страницы или пустую строку в случае ошибки"""

        params = {
            'session': self.session,
            'url': 'https://adeopro.ru/papi/pn',
            'title': 'adeo',
            'params': {'pn': self.search}
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return page


    def get_json(self, text):
        soup = bs4.BeautifulSoup(text, 'lxml').find_all('a')
        part_list_by_originality = {
            'original': [],
            'analog': []
        }
        for variant in soup:  # перебор предложенных найденных брендов
            for origins in 'original', 'analog':  # формирование параметров для парсинга каждой отдельной страницы
                s = variant['href'].strip().split('&')
                data = {
                    'kind': '3' if origins == 'original' else '4',
                    'pn': s[0][7:],
                    'brand': s[1][6:],
                    'limit_good_offers': '5'
                }
                params = {
                    'session': self.session,
                    'url': 'https://adeopro.ru/papi/price_part',
                    'params': data,
                    'headers': {
                        'cookie': f'LegacyApp={self.legacy_app};REMEMBERME={self.remember_me}',
                        'User-Agent': UserAgent().random,
                        'accept': 'application/json',
                    },
                    'title': 'adeo'
                }
                page = Service(params).checking_page_loading()
                if page.json()['items']:
                    part_list_by_originality[origins].extend(page.json()['items'])
        return part_list_by_originality

    def parse_json(self, array):
        for block in array[1]:

            url = f"https://adeopro.ru/pn?pn={block['pn_clean']}&brand={block['provider_original_name']}"
            if not url:
                logger.error('no href')
                continue

            number = block['pn_clean']
            if not number:
                logger.error('no article')
                continue

            brand_name = block['provider_original_name']
            if not brand_name:
                logger.error('no brand name')

            goods_name = block['pn_price_desc']
            if not goods_name:
                logger.error('no info')

            price = int(block['cost_sale_format'].replace(" ", ""))
            if not price:
                logger.error('no price')
                continue

            date = block['due_date_true']
            if not date:
                logger.error('no delivery date')
                continue

            original = array[0]
            if not original:
                logger.error('no originality')
                continue

            if block['pfid'] != None:
                image_url = f'https://adeopro.ru/papi/partsphoto.php?nr={number}&tp=1&firm={brand_name}&index=0&snapshot=0'
            else:
                image_url = 'no url'

            self.result.append({
                'originality': original,
                'brand_name': brand_name,
                'finis': number,
                'goods_name': goods_name,
                'delivery_date': date,
                'price': price,
                'url': url,
                'image_url': image_url
            })
        return

    def run(self):
        """Осуществляет валидность полученных данных и возвращает результатами работы парсера в виде списка предложений
        по выбранному артикулу. При возникновении ошибки прекращает дальнейшую обработку данных и возвращает пустой
        список в качестве результата."""

        offer_list = self.get_offer_list()
        if offer_list:
            part_list = self.get_json(offer_list)
            if len(part_list['original']) == 0 and len(part_list['analog']) == 0:
                return self.result
            with ThreadPoolExecutor(8) as thread:
                thread.map(self.parse_json, [(k, v) for k, v in part_list.items()])
            logger.info(f'adeo.pro: Получено {len(self.result)} элементов')
        return self.result
