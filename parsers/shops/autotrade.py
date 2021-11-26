import logging
from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from main.models import Cookie
from fake_useragent import UserAgent
from .services import Service
from concurrent.futures import ThreadPoolExecutor

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')

# TODO возможно придётся удалить

class AutoTrade:

    def __init__(self, search=''):
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='autotrade').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search
        self.headers = {'User-Agent': UserAgent().random}

    def get_page(self, url=''):
        params = {
            'session': self.session,
            'url': url,
            'title': 'autotrade.get_page'
        }
        page = Service(params).checking_page_loading()
        if page:
            return page.text
        return ''

    # def check_of_response(self, text):
    #     """Проверяет ответ на наличие результатов:
    #     В случае их отсутствия возвращает пустой список.
    #     Если по искомому артикулу имеются предложения, то определяет их количество.
    #     Если в качестве ответа искомый товар - возвращает страницу для дальнейшего поиска результатов.
    #     В случае множества предложений составляет список из URL этих предложений и осуществляет поиск страниц с
    #     предложениями согласно списку и возвращает их."""
    #     container = []
    #     soup = BeautifulSoup(text, 'lxml')
    #     if not soup:
    #         logger.info(f"Oops. it didn't work out to cook soup for <autorus>!")
    #         return container
    #     # проверка ответа на запрос
    #     attention = soup.find('div', class_='wFeedback clearfix')
    #     if not attention:
    #         # проверка наличия дополнительях ссылок
    #         marker = soup.find('table', id='searchResultsTable')
    #         if marker:
    #             # поиск предлжений сразу на странице
    #             container.append(soup)
    #         else:
    #             # поиск ссылок на похожие артикулы
    #             list_of_link = []
    #             rows = soup.find_all('a', class_='startSearching')
    #             for row in rows:
    #                 link = f"https://b2b.autorus.ru{row['href']}"
    #                 if not link:
    #                     continue
    #                 list_of_link.append(link)
    #             for link in list_of_link:
    #                 page_by_link = self.get_page(link)
    #                 if page_by_link:
    #                     page = self.check_of_response(page_by_link)
    #                     if page:
    #                         container.append(page)
    #     return container
    #
    # def parse_page(self, container):
    #     blocks_list = []
    #     for page in container:
    #         # проверка ответа на кнопки "Ещё аналоги"
    #         button = page.find('td', id='showMoreAnalogs')
    #         if button:
    #             # дозагрузка даннных
    #             data_block = page.find('div', id='tplData')
    #             params = {
    #                 'url': 'https://b2b.autorus.ru/searchResults',
    #                 'session': self.session,
    #                 'title': 'autorus',
    #                 'params': {
    #                     'action': 'showMoreAnalogs',
    #                     'searchBrand': data_block['searchbrand'],
    #                     'searchNumber': data_block['searchnumber'],
    #                     'resellerId': data_block['resellerid'],
    #                     'customerIdForSearch': data_block['customeridforsearch'],
    #                     'customerIdForPrice': data_block['customeridforprice'],
    #                     'enc': ''
    #                 }
    #             }
    #             additional_page = Service(params).checking_page_loading()
    #             if additional_page:
    #                 soup = BeautifulSoup(additional_page.text, 'lxml')
    #                 blocks_list.extend(soup.find_all('tr', class_='resultTr2'))
    #         blocks_list.extend(page.find_all('tr', class_='resultTr2'))
    #     return blocks_list
    #
    # def parsing_block(self, block):
    #     if not block['data-availability']:
    #         return
    #
    #     quality = block['data-is-quality-brand'] or 0
    #     is_analog = block['data-is-analog'] or 0
    #     dict_of_originality = {
    #         (0, 0): 'original',
    #         (1, 1): 'original_replacement',
    #         (0, 1): 'analog'
    #     }
    #     original = dict_of_originality[(int(quality), int(is_analog))]
    #     if not original:
    #         logger.error('no originality')
    #     url = f"https://b2b.autorus.ru{block.find('div', class_='brand').a['href']}"
    #     if not url:
    #         logger.error('no href')
    #
    #     brand_number_img_data = block.find('img', class_='searchResultImg')
    #     brand_name = brand_number_img_data['data-brand']
    #     if not brand_name:
    #         logger.error('no brand name')
    #
    #     number = brand_number_img_data['data-number']
    #     if not number:
    #         logger.error('no finis')
    #
    #     goods_name = block.find('td', class_='resultDescription').text.strip()
    #     if not goods_name:
    #         logger.error('no info')
    #
    #     delivery_date_row = block.find('td', class_='resultDeadline')
    #     delivery_date = 99
    #     if delivery_date_row:
    #         delivery_date_row = delivery_date_row.text.strip()
    #         if 'На складе' in delivery_date_row:
    #             delivery_date = 1
    #         elif 'час' in delivery_date_row:
    #             hrs = int(delivery_date_row.split()[-2])
    #             delivery_date = hrs // 24 + 1 if hrs % 24 > 0 else hrs//24
    #         elif 'дн' in delivery_date_row:
    #             delivery_date = int(delivery_date_row.split()[-2])
    #     else:
    #         logger.error('no delivery date')
    #
    #
    #     price = block.find('td', class_='resultPrice').text.strip()
    #     if price:
    #         price = float(price.split(' руб')[0].replace(' ', '').replace(',', '.'))
    #     else:
    #         logger.error('no price')
    #
    #     no_img = '05ec2886842e3204c84e1560b0b40a7964.png'
    #     image_src = brand_number_img_data['src']
    #     image_url = 'no url'
    #     if image_src:
    #         image_url = image_src if no_img not in image_src else 'no url'
    #
    #     self.result.append({
    #         'originality': original,
    #         'brand_name': brand_name,
    #         'finis': number,
    #         'goods_name': goods_name,
    #         'delivery_date': delivery_date,
    #         'price': price,
    #         'url': url,
    #         'image_url': image_url
    #     })


    def run(self):
        text = self.get_page(url=f'https://b2b.autorus.ru/search/?pcode={self.search}&whCode=')
        # if text:
        #     container = self.check_of_response(text=text)
        #     if container:
        #         blocks = self.parse_page(container)
        #         if blocks:
        #             with ThreadPoolExecutor(len(blocks) // 10) as thread:
        #                 thread.map(self.parsing_block, blocks)
        logger.info(f'autorus: Получено {len(self.result)} элементов')
        return self.result
