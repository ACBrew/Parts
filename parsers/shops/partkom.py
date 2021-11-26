import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from .services import Service
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class PartKom:

    def __init__(self, search=''):
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='part-kom').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search
        self.headers = {'User-Agent': UserAgent().random}

    def get_page(self, maker_id=''):
        """Возвращает HTML-код страницы или пустую строку в случае ошибки"""
        params = {
            'session': self.session,
            'url': 'http://www.part-kom.ru/search/',
            'title': 'partkom',
            'params': {
                'number': self.search,
                'maker_id': maker_id,
                'excSubstitutes': '0',
                'excAnalogues': '0',
                'txtAddPrice': '0',
                'stores': '1',
            }}
        page = Service(params).checking_page_loading()
        if page:
            return page.json()
        return page

    def get_offers(self, page):
        offers_list = []
        if page['makers']:
            for offer in page['makers']:  # перебор предложенных найденных брендов
                offers_list.append(self.get_page(maker_id=offer['id']))
        return offers_list

    def parse_json(self, offers):
        origins = {
            'exact': 'original',
            'substitute': 'original_replacement',
            'analogue': 'analog'
        }
        for key in origins:
            if offers.get(key, False):
                for block in offers[key]:
                    if block.get('offers', False):
                        for offer in block['offers']:
                            str_id = block['id'].split(':')
                            url = f"http://www.part-kom.ru/new/#/search/0/0/0/{str_id[0]}/{str_id[1]}"
                            if not url:
                                logger.error('no href')

                            number = offer['number']
                            if not number:
                                logger.error('no finis')

                            brand_name = offer['maker_name']
                            if not brand_name:
                                logger.error('no brand name')

                            goods_name = offer['description']
                            if not goods_name:
                                logger.error('no info')

                            price = float(offer['price'])
                            if not price:
                                logger.error('no price')

                            date = [d['deliveryCountDay'] for d in offers['providers'] if
                                    d['id'] == offer['source_provider_id']][0]
                            if not date and date != 0:
                                logger.error('no delivery date')

                            original = origins[key]
                            if not original:
                                logger.error('no originality')

                            image_url = 'no url'
                            # Требует дополнительный запрос по ссылке и парсига url картинки из ответа за запрос
                            # if block['img']:
                            #     image_url = f"http://www.part-kom.ru/parts/details.php?txtNumber={number}" \
                            #                 f"&txtMaker={brand_name}&part_id={offer['part_id']}"

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
        page = self.get_page()
        if page:
            offer_list = self.get_offers(page)
            if offer_list:
                with ThreadPoolExecutor(5) as thread:
                    thread.map(self.parse_json, offer_list)
        logger.info(f'part-kom: Получено {len(self.result)} элементов')
        return self.result
