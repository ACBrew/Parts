import logging
from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
from fake_useragent import UserAgent
from .services import Service
from concurrent.futures import ThreadPoolExecutor

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class Exist():

    def __init__(self, search=''):
        self.session = requests.Session()
        self.z = Cookie.objects.filter(title='exist').values('value')[0]['value']
        self.result = []
        self.search = search
        self.headers = {'User-Agent': UserAgent().random, 'cookie': f"_z2={self.z}"}

    def get_page(self, url=''):
        params = {
            'session': self.session,
            'url': url,
            'title': 'exist.get_page',
            'params': {'pcode': self.search},
            'headers': self.headers,
            'timeout': (2, 7)
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return ''

    def check_of_response(self, text):
        """Проверяет ответ на наличие результатов:
        В случае их отсутствия возвращает пустой список.
        Если по искомому артикулу имеются предложения, то определяет их количество.
        Если в качестве ответа искомый товар - возвращает страницу для дальнейшего поиска результатов.
        В случае множества предложений составляет список из URL этих предложений и осуществляет поиск страниц с
        предложениями согласно списку и возвращает их."""
        container = []
        soup = BeautifulSoup(text, 'lxml')
        if not soup:
            logger.info(f"Oops. it didn't work out to cook soup for <exist>!")
            return container
        # проверка ответа на запрос
        message = soup.find('div', class_='aspNetHidden')
        if message:
            attention = True if 'По вашему запросу ничего не найдено' in message.text else False
        else:
            return container
        if not attention:
            # проверка наличия дополнительях ссылок
            marker = soup.find('ul', class_='catalogs')
            if not marker:
                # поиск предлжений сразу на странице
                return soup
            else:
                # поиск ссылок на похожие артикулы
                list_of_link = [f"https://exist.ru{i['href']}" for i in
                                soup.find('ul', class_='catalogs').find_all('a')]
                for link in list_of_link:
                    page_by_link = self.get_page(link)
                    if page_by_link:
                        page = self.check_of_response(page_by_link)
                        if page:
                            container.append(page)
        return container

    def get_json_list(self, container):
        """ Осуществляет проверку спарсенных страниц на наличие скрипта, представляющего собой список словарей. При
            его наличии преобразует его в json, а затем возвращает последний. В случает отсутствия — возвращает
            пустой словарь"""
        json_list = []
        for el in container:
            section = [json_dict for json_dict in el.find_all('script', type="text/javascript") if
                       'var _data' in str(json_dict)]
            for script in section:
                script.encoding = 'utf8'
                json_list.extend(json.loads(str(script).split('var _data = ')[1].split('; var ')[0]))
        return json_list

    def parsing_json(self, block):
        origins = {
            'Запрошенный артикул': 'original',
            'Другая упаковка': 'original',
            'Предложения по оригинальным производителям': 'original',
            'Предложения по заменителям': 'analog',
            'Артикулы с улучшенными характеристиками': 'original_replacement'
        }
        if block['AggregatedParts']:
            for el in block['AggregatedParts']:

                url = f"https://exist.ru/Price/?pid={block['ProductIdEnc']}"
                if not url:
                    logger.error('no href')
                    continue

                brand_name = block['CatalogName']
                if not brand_name:
                    logger.error('no brand name')

                number = block['PartNumber']
                if not number:
                    logger.error('no number')

                goods_name = block['Description']
                if not goods_name:
                    logger.error('no info')

                price = float(el['price'])
                if not price:
                    logger.error('no price')

                date = el['days']
                if not date and date != 0:
                    logger.error('no delivery date')

                original = origins.get(block['BlockText'], None)
                if not original:
                    logger.error('no originality')
                    continue

                if block['InfoHTML'] and ('img' in block["InfoHTML"]):
                    image_url = self.parse_image_url(f"https://exist.ru/Parts/Float.aspx?"
                                                     f"{block['ProdUrl'].split('?')[1]}")
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

    def parse_image_url(self, url):
        """
        Осуществляет поиск URL-адреса изображения запчасти в спарсенном json файле.
        При наличии изображения возвращает его корректный URL адрес.
        При отсутстви изображения возвращает "no image".
        """
        params = {
            'session': self.session,
            'url': url,
            'title': 'exist.parse_image_url',
            'headers': self.headers
        }
        page = Service(params).checking_page_loading()
        if page:
            soup = BeautifulSoup(page.text, 'lxml')
            image_url = soup.find('a', class_='mainimage').get('href', 'no url')
            return image_url
        return "no url"

    def run(self):
        text = self.get_page('https://exist.ru/Price/')
        if text:
            container = self.check_of_response(text)
            if container:
                json_list = self.get_json_list(container)
                if json_list:
                    with ThreadPoolExecutor(len(json_list) // 10) as thread:
                        thread.map(self.parsing_json, json_list)
        logger.info(f'exist: Получено {len(self.result)} элементов')
        return self.result
