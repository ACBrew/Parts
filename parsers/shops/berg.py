import logging
import bs4
from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from fake_useragent import UserAgent
from .services import Service
from concurrent.futures import ThreadPoolExecutor
import datetime
import urllib3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Berg:

    def __init__(self, search=''):
        # загрузка параметров сессии из базы данных
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='berg').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []  # список для хранения результатов парсинга
        self.search = search
        self.headers = {'User-Agent': UserAgent().random}

    def get_page(self, url=''):
        """Возвращает HTML-код страницы или пустую строку в случае ошибки"""
        params = {
            'session': self.session,
            'url': url,
            'title': 'berg'
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return page

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
            logger.info(f"Oops. it didn't work out to cook soup for <berg>!")
            return []
        # проверка ответа на запрос
        attention = soup.find('div', class_='attention_message')
        if not attention:
            title = soup.find('div', class_='block_title block_title__first')
            if title:
                check_row = title.find('div', class_='block_title__header').text.strip()
            else:
                return []
            # проверка наличия ссылок на похожие артикулы
            if check_row == 'Искомый товар':
                # поиск сразу на странице
                return soup
            elif check_row == 'Точные совпадения по артикулу':
                # поиск ссылок, потом поиск на странице
                list_of_link = []
                rows = soup.find_all('div', class_='search_result__row')
                for row in rows:
                    link = row.find('td', class_='exact__to_offers_col')
                    if not link:
                        continue
                    list_of_link.append('https://berg.ru' + link.find('a')['href'])
                for link in list_of_link:
                    page_by_link = self.get_page(link)
                    if page_by_link:
                        block = self.check_of_response(page_by_link)
                        if block:
                            container.append(block)
            return container
        return []

    def get_offers(self, container):
        list_of_offers = []  # создаем списки для каждой категории оригинальности
        for page in container:
            # проверка наличия пагинации
            paginator_on_page = page.find('div', class_='paginator')
            if paginator_on_page:
                # собираю ссылки для всех страниц кроме первой
                page_link = paginator_on_page.find_all('a', class_='ajax_link')
                # создаю список ссылок
                for i in range(len(page_link)):
                    page_link[i] = 'https://berg.ru' + page_link[i]['href']
                # перехожу по каждой ссылке
                for link in page_link:
                    params = {
                        'session': self.session,
                        'url': link,
                        'title': 'berg',
                        'timeout': (1, 2)
                    }
                    page = Service(params).checking_page_loading()
                    if page:
                        offers = BeautifulSoup(page.text, 'lxml').find_all('div', class_='search_result__row')
                        list_of_offers.extend([{'analog': i} for i in offers[1:]])
            offers = BeautifulSoup(page.text, 'lxml').find_all('div', class_='search_result__row')
            list_of_offers.extend([{'original': i} for i in offers[:1]])
            list_of_offers.extend([{'analog': i} for i in offers[1:]])
        return list_of_offers

    def parsing_offers(self, block):
        for originality, offer in block.items():
            info = offer.find('div', class_='search_card__title_container')

            url = f"https://berg.ru{info.select_one('div.article').select_one('a.ajax_link')['href']}"
            if not url:
                logger.error('no href')
                continue

            brand_name = info.select_one('span.brand_name').text
            if not brand_name:
                logger.error('no brand name')

            number = info.select_one('div.article').select_one('a.ajax_link').text.strip()
            if not number:
                logger.error('no finis')
                continue

            goods_name = info.select_one('div.description').select_one('a.part_description__link')['title']
            if not goods_name:
                logger.error('no info')

            image_url = f"https:{offer.find('div', class_='card_photo').select_one('img')['src']}"
            if image_url == 'https:/bundles/bergsite/new/images/cart_noimg.png?v582':
                image_url = 'no image'

            price_table = offer.find('div', class_='search_card__table')
            if price_table:
                # основные даты/цены поставки
                price_list = price_table.find('div', class_='table__with_card').select('tr', attrs='data-row-id')

                # скрытые даты/цены поставки
                other_off = price_table.find('div', class_='search_result__other_rows')
                if other_off.text.strip():
                    # при наличии делается запрос для получения дополнительных дат/цен поставки
                    link_other_rows = f"https://berg.ru{other_off.select_one('a.expand_rows')['href']}"
                    try:
                        response = self.session.get(url=link_other_rows,
                                                    headers={
                                                        'User-Agent': UserAgent().random,
                                                        'X-Requested-With': 'XMLHttpRequest'},
                                                    verify=False, timeout=(1, 2))
                    except requests.exceptions.ConnectionError:
                        pass
                    else:
                        response.encoding = 'utf-8'
                        response = response.text
                        add_price = BeautifulSoup(response, 'lxml').select('tr', attrs='data-row-id')
                        price_list.extend(add_price)
            else:
                continue

            for el in price_list:
                delivery_date = int(el['data-min-period']) or 0
                price = float(el.select('input')[1]['value'])
                self.result.append({
                    'originality': originality,
                    'brand_name': brand_name,
                    'finis': number,
                    'goods_name': goods_name,
                    'delivery_date': delivery_date,
                    'price': price,
                    'url': url,
                    'image_url': image_url
                })

    def run(self):
        """Осуществляет валидность полученных данных и возвращает результатами работы парсера в виде списка предложений
        по выбранному артикулу.
        При возникновении ошибки прекращает дальнейшую обработку данных и возвращает пустой список в качестве
        результата."""

        text = self.get_page(url=f'https://berg.ru/search?search={self.search}')
        if text:
            container = self.check_of_response(text=text)
            if container:
                offers = []
                if isinstance(container, list):
                    offers = self.get_offers(container)
                elif isinstance(container, bs4.BeautifulSoup):
                    offers = self.get_offers([container])
                if offers:
                    with ThreadPoolExecutor(len(offers) // 10) as thread:
                        thread.map(self.parsing_offers, offers)
        logger.info(f'berg: Получено {len(self.result)} элементов')
        return self.result
