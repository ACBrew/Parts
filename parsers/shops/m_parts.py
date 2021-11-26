import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import hashlib
from .services import Service
from fake_useragent import UserAgent

from concurrent.futures import ThreadPoolExecutor

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class M_Parts():

    def __init__(self, search=''):
        self.session = requests.Session()
        self.result = []
        self.search = search
        self.login = Cookie.objects.filter(title='m-parts.ru')[0].user_login
        self.md5_pass = hashlib.md5(Cookie.objects.filter(title='m-parts.ru')[0].user_password.encode()).hexdigest()
        self.dict_of_original_brands = {}

    def get_brands(self):
        """Возвращает список брендов соответсвующих запрашиваемому артикулу"""
        params = {
            'session': self.session,
            'title': 'm_parts.get_brands',
            'url': f"https://v01.ru/api/devinsight/search/brands/?"
                   f"userlogin={self.login}&userpsw={self.md5_pass}&number={self.search}"
        }
        js_include_brands = Service(params).checking_page_loading()
        if js_include_brands:
            return js_include_brands.json()
        return {}

    def get_offers(self, brands):
        """Осуществляет поиск предложений по полученным брендам и возвращает список предложений по всем брендам, а также
         их аналогам. Дополнительно добавляет в словарь self.dict_of_original_brands информацию об оригинальных артикулах
         и соответствующих им брендам"""
        offers = []
        for variant in brands:
            if brands[variant]['availability']:
                brand = brands[variant]['brand']
                number = brands[variant]['number']
                self.dict_of_original_brands.update({brand: number})
                params = {
                    'session': self.session,
                    'title': 'm_parts.get_brands',
                    'url': f"https://v01.ru/api/devinsight/search/articles/?"
                           f"userlogin={self.login}&userpsw={self.md5_pass}&number={number}&brand={brand}"
                }
                js_include_offers = Service(params).checking_page_loading()
                if js_include_offers:
                    offers.extend(js_include_offers.json())
        return offers

    def parsing_offers(self, offer):

        brand_name = offer['brand']
        if not brand_name:
            logger.error('no brand name')

        number = offer['number']
        if not number:
            logger.error('no finis')

        if brand_name in self.dict_of_original_brands and self.dict_of_original_brands[brand_name] == number:
            original = 'original'
        else:
            original = 'analog'
        if not original:
            logger.error('no originality')

        url = f"http://v01.ru/auto/search/{number}/"
        if not url:
            logger.error('no href')

        goods_name = offer['description']
        if not goods_name:
            logger.error('no info')

        price = float(offer['price'])
        if not price:
            logger.error('no price')

        date = datetime.timedelta(hours=offer['deliveryPeriod']).days
        if not date and date != 0:
            logger.error('no delivery date')

        # Функция self.parse_image_url() рабочая, но было решено её не использовать из-за высокого потребления ресурсов
        # image_url = self.parse_image_url(brand_name, number)
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

    def parse_image_url(self, brand_name, number):
        """Осуществляет поиск URL-адреса изображения запчасти в спарсенном json файле.
        При наличии изображения возвращает его корректный URL адрес.
        При отсутстви изображения возвращает "no image".
        """
        brand_name = brand_name.lower()
        number = number.lower()
        jsonImages = ["{", f'"{brand_name}_{number}"', ":[{", f'"article":"{number}","brand":"{brand_name.upper()}"',
                      "}]}"]
        js = {'jsonImages': ('').join(jsonImages)}
        url = 'http://v01.ru/ajax/productImage.php'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': UserAgent().random,
            'X-Requested-With': 'XMLHttpRequest'
        }
        res = self.session.post(url=url, headers=headers, data=js, verify=False, timeout=(1, 1))
        res.encoding = 'utf8'
        res.raise_for_status()
        return 'http://v01.ru/' + res.json()['FOUND'][f'{brand_name}_{number}'][0]['DETAIL'] if res.json()[
            'FOUND'] else 'no url'

    def run(self):
        brands = self.get_brands()
        if brands:
            offers = self.get_offers(brands)
            if offers:
                with ThreadPoolExecutor(8) as thread:
                    thread.map(self.parsing_offers, offers)
        logger.info(f'm-parts: Получено {len(self.result)} элементов')
        return self.result
