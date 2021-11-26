import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures
from .services import Service

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class AutoEuro:
    # TODO: реализовать хранение ключей api_key и delivery_key в базе данных и их автоматической загрузкой в парсер
    def __init__(self, search=''):
        self.session = requests.Session()
        self.api_key = 'vBbd8XqT3OYwSFFiztDTQ3fImBBFPqvRO8kNMbbcm09VU1Dt85D8hgbKPRKw'
        self.delivery_key = 'DxAiijBmh4sIlDHxWTCkxmTkDp9drWHr4W1cRdt2LjErkxuvfoFsRP2EGmixeBVzSBSkqF1UAILvpPgdt5aCph2JaJkDX2'
        self.result = []  # список для хранения результатов парсинга
        self.search = search

    def get_brand_name(self):
        """Возвращает список брендов, соответствующих искомому артикулу"""

        list_of_brands = []

        params = {
            'session': self.session,
            'url': f'https://api.autoeuro.ru/api/v2/json/search_brands/{self.api_key}',
            'params': {'code': self.search},
            'title': 'autoeuro',
            'timeout': (1, 5)
        }
        page = Service(params).checking_page_loading()
        if page:
            page = page.json()['DATA']
        for brand in page:
            list_of_brands.append(brand['brand'])
        return list_of_brands

    def get_offers(self, list_of_brands):
        """Возвращает список всех предложений по искомому артикулу и брендам из переданного списка"""

        list_offers = []
        for brand in list_of_brands:
            params = {
                'session': self.session,
                'url': f'https://api.autoeuro.ru/api/v2/json/search_items/{self.api_key}',
                'params': {
                    'brand': brand,
                    'code': self.search,
                    'delivery_key': self.delivery_key,
                    'with_crosses': '1',
                    'with_offers': '1'
                },
                'title': 'autoeuro',
                'timeout': (1, 5)
            }
            page = Service(params).checking_page_loading()
            if page:
                list_offers.extend(page.json()['DATA'])
        return list_offers

    def parse_json(self, element):
        originality_dict = {
            None: 'original',
            '0': 'analog',
            '1': 'original_replacement',
            '2': 'analog',
            '3': 'analog',
            '10': 'analog',
            '11': 'analog',
            '12': 'analog'
        }

        number = element['code']
        if not number:
            logger.error('no number')
            return

        url = f"https://shop.autoeuro.ru/main/search?text={number}&whs=&crosses=0&crosses=1"
        if not url:
            logger.error('no href')
            return

        brand_name = element['brand']
        if not brand_name:
            logger.error('no brand name')

        goods_name = element['name']
        if not goods_name:
            logger.error('no info')

        date = element['delivery_time']
        delivery_date = ''
        if date:
            delivery_date = (datetime.strptime(date, '%Y-%m-%d %H:%M').date() - datetime.today().date()).days
        if not delivery_date:
            logger.error('delivery_date')
            return

        price = element['price']
        if not price:
            logger.error('no price')
            return

        image_url = 'no url'
        self.result.append({
            'originality': originality_dict[element['cross']],
            'brand_name': brand_name,
            'finis': number,
            'goods_name': goods_name,
            'delivery_date': delivery_date,
            'price': price,
            'url': url,
            'image_url': image_url
        })
        return

    def run(self):
        list_of_brands = self.get_brand_name()
        if list_of_brands:
            list_of_offers = self.get_offers(list_of_brands)
        else:
            return self.result
        if list_of_offers:
            with futures.ThreadPoolExecutor(len(list_of_offers) // 10) as thread:
                thread.map(self.parse_json, list_of_offers)
        logger.info(f'shop.autoeuro: Получено {len(self.result)} элементов')
        return self.result
