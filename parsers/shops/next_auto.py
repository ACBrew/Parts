import logging
import bs4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from .services import Service

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class NextAuto:

    def __init__(self, search=''):
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='next-auto').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search
        self.headers = {'User-Agent': UserAgent().random}

    # todo Добавить аналог service

    def get_page(self):
        """Возвращает HTML-код страницы или пустую строку в случае ошибки"""

        params = {
            'session': self.session,
            'url': 'http://next-auto.pro/index.php',
            'title': 'next-auto.get_page',
            'params': {'page': 'price'},
            'data': {
                'query': self.search,
                'm': 'any',
                'action': 'shop'
            },
            'method': 'post',
            'timeout': (10, 10)
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return page

    def get_links(self, text):
        """Возвращает список ссылок на выдаваемые сайтом варианты по запрашиваемому артикулу"""
        soup = bs4.BeautifulSoup(text, 'lxml')
        links = []
        section = soup.find('td', id='content').find_all('a')
        if section:
            links = [i['href'] for i in section if not i.has_attr('title')]
        return links

    def get_offers(self, links):
        blocks_list = []
        for link in links:
            # проверка наличия предложений по каждой ссылке
            params_for_link = {i.split('=')[0]: i.split('=')[1] for i in
                               link.split('?')[1].split('&')}  # todo попробовать реализовать через RegEx

            params = {
                'session': self.session,
                'url': link,
                'title': 'next-auto.get_offers',
                'params': params_for_link,
                'method': 'post',
                'timeout': (2, 10),
                'encoding': 'Not encoding'

            }
            page = Service(params).checking_page_loading()
            if page:
                blocks_list.extend(bs4.BeautifulSoup(page.text, 'lxml').find_all('tr', class_='shop_move_out'))
        return blocks_list

    def get_offer(self, block):
        if block.select('.results')[0].select('b'):
            original = 'original'
        else:
            original = 'analog'

        url = block.select_one('a.cart')['onclick'].lstrip("return actQuest('").rstrip("');")

        if not url:
            logger.error('no href')

        brand_name = block.select('.results')[0].td.text.strip().split('-STOCK' or '-EURO22')[0]
        if not brand_name:
            logger.error('no brand name')

        number = block.select('td')[6].text
        if not number:
            logger.error('no finis')

        goods_name = block.select('td')[11].text.encode('ISO-8859-1').decode('cp1251')
        if not goods_name:
            logger.error('no info')

        price = block.select('td')[7].select_one('p').text
        if not price:
            logger.error('no price')

        date = block.select('td')[8].text.split()[0]

        if not date:
            logger.error('no delivery date')

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

    def run(self):
        text = self.get_page()
        if text:
            links = self.get_links(text)
            if links:
                offers = self.get_offers(links)
                if offers:
                    with ThreadPoolExecutor(8) as thread:
                        thread.map(self.get_offer, offers)
        logger.info(f'next-auto: Получено {len(self.result)} элементов')
        return self.result
