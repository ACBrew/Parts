# import fake_useragent
import logging
import bs4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from .models import Parts
from django.db import connection

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ixora-auto')


class ParseResult:

    def __init__(self, finis):
        self.finis = finis
        # pass

    def save_results(self):
        """Сохраняет результаты парсинга сайтов в базу данных Parts, удаляя перед этим все имеющиеся в таблице данные
        """
        result = IxoraAuto(self.finis).run()
        # c = connection.cursor()
        try:
            # query = """DELETE FROM Parts"""
            Parts.objects.all().delete()
            # c.execute(query)
            Parts.objects.bulk_create(result)
            # query = """ INSERT INTO Parts(originality, brand_name, finis, goods_name, delivery_date, price, url, image_url)
            #                          VALUES(%s,%s,%s,%s,%s,%s,%s,%s);"""
            # c.executemany(query, result)
        finally:
            print('gogogo')
            # c.close()

    def search_by_originality(self):

        self.save_results()
        c = connection.cursor()
        try:
            orig = (
                'original',
                'original-replacement',
                'analog'
            )
            query = """SELECT price FROM Parts WHERE originality=%s """
            output = {}
            for i in orig:
                c.execute(query, (i,))
                massive_big = c.fetchall()
                mass = [None, None]
                try:
                    mass[0], mass[1] = min(int(j) for i in massive_big for j in i), max(
                        int(j) for i in massive_big for j in i),
                except:
                    mass[0], mass[1] = 'Категория отсутствует', ''
                output[i] = mass
        finally:
            c.close()
        return output

    def search_by_brands(self, orig):
        self.orig = orig

        c = connection.cursor()
        try:
            query = """WITH
                            cte1 AS ( SELECT *, 
                                 ROW_NUMBER() OVER (PARTITION BY finis ORDER BY price ASC) AS num
                       FROM Parts 
                       WHERE originality=%s ),
                            cte2 AS ( SELECT *,
                                 MIN(price) OVER (PARTITION BY finis) minprice
                       FROM cte1
                       WHERE num <=3 )
                       SELECT * 
                       FROM cte2
                       ORDER BY minprice, num, price;
                        """
            output = {}
            c.execute(query, (self.orig,))
            output = c.fetchall()
        finally:
            c.close()

        return output

    def search_by_selected_brand(self):
        pass


class IxoraAuto:

    def __init__(self, search=''):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 YaBrowser/21.5.1.330 Yowser/2.5 Safari/537.36',
            'Accept-language': 'ru',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8, application/signed-exchange;v=b3;q=0.9'
        }
        # self.search_query = search_query
        self.result = []
        self.search = search

    def load_page(self, page: int = None, params=''):
        search_parameters = {
            'DetailNumber': self.search
        }
        url = 'https://b2b.ixora-auto.ru/Shop/Search.html'
        res = self.session.get(url, params=search_parameters, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        return res.text

    def parse_page(self, text: str):
        soup = bs4.BeautifulSoup(text, 'lxml')
        head_index = 0
        variants = {'tr.O': 'original', 'tr.OR': 'original_replacement', 'tr.R': 'analog'}
        for key, value in variants.items():
            container = soup.select(key)
            for block in container:
                previous_index = head_index
                head_index = int(block['head-index'])
                if previous_index == head_index:
                    self.parse_block(block=block, origins=value, check=True)
                else:
                    self.parse_block(block=block, origins=value, check=False)

    def parse_block(self, block, origins, check):

        if not check:
            url_block = block.select_one("a.SearchDetailFromTable.WithWorkPageUID")

            if not url_block:
                logger.error('no url block')
                return

            url = "https://b2b.ixora-auto.ru" + url_block['href']
            if not url:
                logger.error('no href')

            number = block.select_one('td.DetailName').select_one('a[detailnumber]')['detailnumber'].strip()
            if not number:
                logger.error('no finis')

            info = block.select_one('td.DetailName').text
            if not info:
                logger.error('no info')

            brand_name = info.replace('\r', '').replace('\n', '').partition(number)[0].strip()
            if not brand_name:
                logger.error('no brand name')

            goods_name = info.replace('\r', '').replace('\n', '').partition(number)[2].strip()
            if not goods_name:
                logger.error('no info')

            all_text = block.get_text().split()
            for i in range(len(all_text)):
                if all_text[i] == 'дн.':
                    date = "".join(map(str, all_text[i - 1:i + 1]))
                if all_text[i] == 'наличии':
                    date = 'в наличии'

            price = int(block.find('td', class_='PriceDiscount').text.strip()[:-2])
            if not price:
                logger.error('no price')

            all_text = block.get_text().split()
            for i in range(len(all_text)):
                if all_text[i] == 'дн.':
                    date = "".join(map(str, all_text[i - 1:i + 1]))
            if not date:
                logger.error('no finis')

            original = str(origins)
            if not url:
                logger.error('no href')

            image_url = self.parse_image_url(block)

        else:
            all_text = block.get_text().split()
            for i in range(len(all_text)):
                if all_text[i] == 'дн.':
                    date = "".join(map(str, all_text[i - 1:i + 1]))
                if all_text[i] == 'наличии':
                    date = 'в наличии'

            price = int(block.find('td', class_='PriceDiscount').text.strip()[:-2])
            url = self.result[-1].url
            original = self.result[-1].originality
            brand_name = self.result[-1].brand_name
            goods_name = self.result[-1].goods_name
            number = self.result[-1].finis
            image_url = self.parse_image_url(block)

        p = Parts()
        p.originality = original,
        p.brand_name = brand_name,
        p.finis = number,
        p.goods_name = goods_name,
        p.delivery_date = date,
        p.price = price,
        p.url = url,
        p.image_url = image_url

        self.result.append(p)

    def parse_image_url(self, block):  ### добавить проверку [i]

        """
        Осуществляет поиск URL-адреса изображения запчасти в спарсенном блоке HTML-кода.
        При наличии изображения возвращает его корректный URL адрес.
        При отсутстви изображения возвращает "no image".

        """
        try:
            url = requests.get(
                "https://b2b.ixora-auto.ru" + block.select_one('td.DetailName').select_one('a[href-data]')['href-data']
            )
            text = url.json()[0]['Link']
            return f'https://b2b.ixora-auto.ru{text}'
        except:
            return f'no url'

    def run(self):
        text = self.load_page()
        self.parse_page(text=text)
        logger.info(f'Получено {len(self.result)} элементов')
        return self.result


class Autorization:

    def __init__(self):
        pass

    # def CreateCookiesFile(self):
    #     session = requests.Session()
    #     link = "https://b2b.ixora-auto.ru/Account/LogOn.html"
    #     user = fake_useragent.UserAgent().random
    #     header = {
    #         'user-agent': user
    #     }
    #     data = {
    #         'UserName': 'SVETLN',
    #         'Password': 'ryhw7big'
    #     }
    #     cookies_dict = [
    #         {'domain': key.domain, 'name': key.name, 'path': key.path, 'value': key.value}
    #         for key in session.cookies
    #     ]
    #     for
    #     response = session.post(link, data=data, headers=header)
