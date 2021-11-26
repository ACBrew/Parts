import logging
import bs4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
import datetime
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
from .services import Service


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class IxoraAuto():

    def __init__(self, search=''):
        # загрузка параметров сессии из базы данных
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='ixora-auto').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []  # список для хранения результатов парсинга
        self.search = search
        self.variants = {'O': 'original', 'OR': 'original_replacement', 'R': 'analog'}

    def get_page(self):
        """Возвращает HTML-код страницы или пустую строку в случае ошибки"""

        params = {
            'session': self.session,
            'url': 'https://b2b.ixora-auto.ru/Shop/Search.html',
            'title': 'ixora-auto',
            'params': {'DetailNumber': self.search}
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return page

    def get_blocks(self, text: str):
        """Переданный в качестве первого аругмента, HTML-код страницы содержит табицу, состоящую из предложений по
        запрашиваемой детали, а также её аналогам и оригинальным заменителям. Данная функция делит табицу на блоки
        согласно оригинальности детали и возвращает их """

        soup = bs4.BeautifulSoup(text, 'lxml').find('table', class_='ObjectForAddLoad')
        sorted_blocks = {}
        container = []
        if not soup:
            logger.info(f"Oops. it didn't work out to cook soup for <ixora-auto>!")
            return sorted_blocks
        for key in self.variants:
            container += soup.find_all('tr', class_=key)

        '''Информация о доступных предложениях представлена в виде строк, каждая из которых разбита на подстроки 
        и часть данных содержится лишь в первой подстроке. Строка и её подстроки содержат уникальный индекс, по 
        которому происходит сортировка строк и всех её подстрок'''

        if container:
            for block in container:
                if sorted_blocks.get(block['head-index']):
                    sorted_blocks[block['head-index']].append(block)
                else:
                    sorted_blocks[block['head-index']] = [block]
        return sorted_blocks

    def parsing_blocks(self, value):
        """Добавляет в список self.result предложения по искомому артикулу. Каждый элемент списка является словарём.
        Разбирает blocks на списки. Часть информации о запчасти (оригинальность, артикул, название бренда, описание
        запчасти и url-адрес) находится только в первом элементе списка"""

        month = {
            'янв': '1',
            'фев': '2',
            'мар': '3',
            'апр': '4',
            'май': '5',
            'июн': '6',
            'июл': '7',
            'авг': '8',
            'сен': '9',
            'окт': '10',
            'ноя': '11',
            'дек': '12'
        }

        original = self.variants[value[0].td['class'][1]]

        info = value[0].select_one('td.DetailName').text

        if not info:
            logger.error('no info')

        number = value[0].select_one('td.DetailName').select_one('a[detailnumber]')['detailnumber'].strip()
        if not number:
            logger.error('no finis')

        brand_name = info.replace('\r', '').replace('\n', '').partition(number)[0].strip()
        if not brand_name:
            logger.error('no brand name')

        goods_name = info.replace('\r', '').replace('\n', '').partition(number)[2].strip()
        if not goods_name:
            logger.error(f'no description for {number}')
            goods_name = 'Описание отсутствует'

        url = "https://b2b.ixora-auto.ru" + value[0].select_one('a.SearchDetailFromTable')['href']
        if not url:
            logger.error('no href')

        for el in value:
            date_row = el.select_one('span.delivery_date_action').text.split()
            date_row[1] = [v for k, v in month.items() if str(k) in date_row[1]][0]
            date = int(str(datetime.date(datetime.date.today().year, int(date_row[1]),
                                         int(date_row[0])) - datetime.date.today()).split()[0])
            if not date:
                date = 'no delivery date'
                logger.error('no delivery date')

            price = float(el.find('td', class_='PriceDiscount').text.replace(',', '.'))
            if not price:
                price = 'no price'
                logger.error('no price')

            image_url = self.get_image_url(el)

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

    def get_image_url(self, block):  # TODO: добавить проверку [i]

        """
        Осуществляет поиск URL-адреса изображения запчасти в спарсенном блоке HTML-кода.
        При наличии изображения возвращает его корректный URL адрес.
        При отсутстви изображения возвращает "no image".

        """
        try:
            url = requests.get(
                "https://b2b.ixora-auto.ru" + block.select_one('td.DetailName').select_one('a[href-data]')['href-data']
            )
        except:
            return f'no url'
        text = url.json()[0]['Link']
        return f'https://b2b.ixora-auto.ru{text}'

    def run(self):
        """Осуществляет валидность полученных данных и возвращает результатами работы парсера в виде списка предложений
        по выбранному артикулу.
        При возникновении ошибки прекращает дальнейшую обработку данных и возвращает пустой список в качестве
        результата."""
        text = self.get_page()
        if text:
            sorted_blocks = self.get_blocks(text=text)
        else:
            return self.result
        if sorted_blocks:
            with ThreadPoolExecutor(len(sorted_blocks)//10) as thread:
                thread.map(self.parsing_blocks, list(sorted_blocks.values()))
            logger.info(f'ixora-auto: Получено {len(self.result)} элементов')
        return self.result

