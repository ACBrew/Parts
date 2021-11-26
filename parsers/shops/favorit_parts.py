import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from .services import Service
from concurrent.futures import ThreadPoolExecutor

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class FavoritParts:

    def __init__(self, search=''):
        self.session = requests.Session()
        self.api_key = "01C96421-CAC2-11E3-9DC8-0050568E0E34"  # todo реализовать алгоритм добывания ключа из профиля
        self.result = []
        self.search = search
        self.params = {
            'session': self.session,
            'title': 'favorit_parts.get_brands',
            'url': 'http://api.favorit-parts.ru/hs/hsprice/',
            'params': {
                'key': self.api_key,
                'number': self.search,
                'analogues': 'on'
            }
        }

    def get_brands(self):
        js_include_brands = Service(self.params).checking_page_loading()
        if js_include_brands:
            return js_include_brands.json()
        return {}

    def get_offers(self, js_include_brands):
        brands = [i['brand'] for i in js_include_brands['goods']]
        for brand in brands:  # перебор предложенных найденных брендов
            params = self.params
            params['params'] = params['params'] | {'brand': brand}
            js_include_offers = Service(params).checking_page_loading()
            if js_include_offers:
                return js_include_offers.json()['goods'][0]
            return {}

    def sort_offers(self, offers):
        blocks = []
        if offers.get('brand', '') and offers.get('warehouses', []):
            blocks.append({'originality': 'original',
                           'brand': offers['brand'],
                           'name': offers['name'],
                           'number': offers['number'],
                           'warehouses': offers['warehouses']})
        if offers.get('analogues', []):
            blocks.extend({'originality': 'analog'} | i for i in offers['analogues'])
        return blocks

    def parsing_block(self, block):
        if block['warehouses']:
            for warehouse in block['warehouses']:
                brand_name = block['brand']
                number = block['number']
                goods_name = block['name']
                url = f"https://favorit-parts.ru/search/?number={number}"
                price = warehouse['price']

                date_row = datetime.datetime.fromisoformat(warehouse['shipmentDate']).date()
                delivery_date = (date_row - datetime.datetime.today().date()).days
                self.result.append({
                    'originality': block['originality'],
                    'brand_name': brand_name,
                    'finis': number,
                    'goods_name': goods_name,
                    'delivery_date': delivery_date,
                    'price': price,
                    'url': url,
                    'image_url': 'no url'
                })
        return

    def run(self):
        brands = self.get_brands()
        if brands:
            offers = self.get_offers(brands)
            if offers:
                blocks = self.sort_offers(offers)
                if blocks:
                    with ThreadPoolExecutor(len(blocks) // 10) as thread:
                        thread.map(self.parsing_block, blocks)
        logger.info(f'favorit-parts: Получено {len(self.result)} элементов')
        return self.result
