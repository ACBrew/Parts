from django.shortcuts import render
import logging
import bs4
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from .models import Parts
from main.models import Cookie, Xhr
from django.db import connection
import datetime
import xmltodict
from fake_useragent import UserAgent
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from django.db.models import Avg, Max, Min
import json
import hashlib

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')

# TODO: при запуске приложения автомитически обновлять данные в табицах Cookies и XHR
def save_results(finis):
    """Сохраняет результаты парсинга сайтов в базу данных Parts, удаляя перед этим все имеющиеся в таблице данные
    """
    pars = [
        # IxoraAuto,
        # Rossko,
        # Adeo,
        # NextAuto,
        # PartKom,
        # AutoEuro,
        # FavoritParts,
        # Exist,
        M_Parts,
        # STParts
    ]
    result = []
    for i in pars:
        # try:
        result += i(finis).run()
        # except:
        #     continue
    Parts.objects.all().delete()
    with connection.cursor() as c:
        try:
            c.execute("""
    UPDATE sqlite_sequence SET seq = 0 FROM parsers_parts""")

        except:
            pass
    Parts.objects.bulk_create(Parts(**val) for val in result)


def index(request):
    """Производит поиск введенного артикула по заданнным сайтам используя авторизацию или API (если доступно).
    Полученные данные сохраняются в виде объектов модели Parts, уже существующие объекты при этом удаляются.
    Затем полученные объекты сортируются по полю originality и выводятся в шаблоне виде 1-3 блоков содержащих
    значение originality и соответствующий данному значению диапазон знчений поля price.
    В случае, если искомый артикул не найден на экран выводится соответствующее сообщение.
    """
    if request.method == 'GET':
        finis = request.GET.get('q')
    save_results(finis=finis)
    variants_of_originality = (
        'original',
        'original-replacement',
        'analog'
    )

    output = {}
    for i in variants_of_originality:
        output[i] = Parts.objects.filter(originality=i).aggregate(Min('price'), Max('price'))
    context = {
        'title': 'Вывод первых результатов',
        'ss': output
    }
    for k in list(context['ss']):
        if context['ss'][k]['price__min'] == None:
            del context['ss'][k]
    if not context['ss']:
        data = {
            'title': f'{finis} не найден!!!',
            'message': f' '  # "{finis}"?????'
            # f'Неверный запрос'
        }
        return render(request, 'main/index.html', data)
    return render(request, 'parsers/index.html', context)


def sort_by_origins(request):
    """Получает объекты Parts согласно выбранной ранее категории originality. Объекты группируются по полю finis, затем внутри
    каждой группы происходит сортировка по полю price. После этого группы выводятся на экран в воде блоков, отсортированных
    по наименьшим значениям полей price в каждой из групп. Каждый блок содержит не более 3 объектов.
    """
    if request.method == 'POST':
        marker = request.POST['original']
    else:
        marker = 'не сработало!'
    sort_data = {}
    c = connection.cursor()
    # TODO: Переделать запрос под Django ORM
    try:
        query = """WITH
                        cte1 AS ( SELECT *, 
                             ROW_NUMBER() OVER (PARTITION BY finis ORDER BY price ASC) AS num
                   FROM parsers_parts 
                   WHERE originality=%s ),
                        cte2 AS ( SELECT *,
                             MIN(price) OVER (PARTITION BY finis) minprice
                   FROM cte1
                   WHERE num <=3 )
                   SELECT originality,brand_name,finis,goods_name,delivery_date,price,url,image_url
                   FROM cte2
                   ORDER BY minprice, num, price;
                    """
        c.execute(query, (marker,))
        sort_data = c.fetchall()
    finally:
        c.close()

    marker_dict = {
        'original': f'Предложения по запрашиваемому артикулу',
        'original-replacement': f'Предложения по ориганальным заменителям',
        'analog': f'Предложения по заменителям'
    }
    data = {
        'original': marker,
        'title': marker_dict[marker],
        'sort_data': sort_data
    }
    return render(request, 'parsers/index2.html', data)


def sort_by_selected_brand(request):
    """Получает все объекты Parts согласно выбранному ранее finis. Объекты сортируются по полю price и выводятся в виде
    списка на экран
    """
    if request.method == 'GET':
        finis = request.GET.get('finis')
    sort_data = Parts.objects.filter(finis=finis).order_by('price')
    data = {
        'title': 'Все предложения по выбранному артикулу',
        'sort_data': sort_data
    }
    return render(request, 'parsers/index3.html', data)

# class PartsParser: # TODO: создать родительский класс для парсеров
#
#     def __init__(self, search='',title):
#         self.session = requests.Session()
#         cookies_dict = [
#             {'domain': key.domain,
#              'name': key.name,
#              'path': key.path,
#              'value': key.value}
#             for key in Cookie.objects.filter(title=title).all()
#         ]
#         for cookies in cookies_dict:
#             self.session.cookies.set(**cookies)
#         self.result = []
#         self.search = search


class IxoraAuto():

    def __init__(self, search='', title='ixora-auto'):
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
        self.result = []
        self.search = search

    def load_page(self, page: int = None, params=''):
        search_parameters = {
            'DetailNumber': self.search
        }
        url = 'https://b2b.ixora-auto.ru/Shop/Search.html'
        headers = {'User-Agent': UserAgent().random}
        res = self.session.get(url, params=search_parameters, headers=headers, verify=False)
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
        date_row = block.select_one('span.delivery_date_action').text.split()
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

            price = float(block.find('td', class_='PriceDiscount').text.replace(',', '.'))
            if not price:
                logger.error('no price')

            date_row[1] = [v for k, v in month.items() if str(k) in date_row[1]][0]
            date = int(str(datetime.date(datetime.date.today().year, int(date_row[1]),
                                         int(date_row[0])) - datetime.date.today()).split()[0])

            if not date:
                logger.error('no delivery date')

            original = str(origins)
            if not url:
                logger.error('no href')

            image_url = self.parse_image_url(block)

        else:

            date_row[1] = [v for k, v in month.items() if str(k) in date_row[1]][0]
            date = int(str(datetime.date(datetime.date.today().year, int(date_row[1]),
                                         int(date_row[0])) - datetime.date.today()).split()[0])

            price = float(block.find('td', class_='PriceDiscount').text.replace(',', '.'))
            url = self.result[-1]['url']
            original = self.result[-1]['originality']
            brand_name = self.result[-1]['brand_name']
            goods_name = self.result[-1]['goods_name']
            number = self.result[-1]['finis']
            image_url = self.parse_image_url(block)

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

    def parse_image_url(self, block):  # TODO: добавить проверку [i]

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
        logger.info(f'ixora-auto: Получено {len(self.result)} элементов')
        return self.result


class Rossko:  # TODO: попробовать спарсить изображения

    def __init__(self, search=''):
        self.search = search

    def array_append(self, arr, section, warehouse, orig):
        arr.append({
            'originality': orig,
            'brand_name': section['ns1:brand'],
            'finis': section['ns1:partnumber'],
            'goods_name': section['ns1:name'] or 'Описание отсутствует',
            'delivery_date': warehouse['ns1:delivery'],
            'price': warehouse['ns1:price'],
            'url': 'https://penza.rossko.ru/product?text=' + section['ns1:guid'],
            'image_url': 'no url'
        })

    # def get_image_url(link):
    #     session = requests.Session()
    #     session.headers = {
    #         'User-Agent': fake_useragent.UserAgent().random,
    #         'Accept-language': 'ru',
    #         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8, application/signed-exchange;v=b3;q=0.9'
    #     }
    #     res = session.get(link, verify=False)
    #     res.encoding = 'utf8'
    #     res.raise_for_status()
    #     soup = bs4.BeautifulSoup(res.text, 'lxml')
    #     # number = block.select_one('td.DetailName').select_one('a[detailnumber]')['detailnumber'].strip()
    #
    #     img_url = soup.find_all("div", class_="src-features-product-card-containers-___index__wrap___3d8sC")
    #     # img_url = soup.findAll('div', class_='src-features-product-card-components-oldInfo-___index__image')
    #     return img_url
    def parse_page(self):

        key_1 = 'cf947057674a3f96aba069db6e0b1e73'
        key_2 = '9379490cbcde554d90404df9307c0444'

        get_search = 'http://api.rossko.ru/service/v2.1/GetSearch'
        headers = {'content-type': 'application/soap+xml; charset=utf-8'}
        adress_id = '42716'
        body_search = {
            'KEY1': key_1,
            'KEY2': key_2,
        }

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:api="http://api.rossko.ru/">
           <soapenv:Header/>
           <soapenv:Body>
              <api:GetSearch>
                 <api:KEY1>{body_search['KEY1']}</api:KEY1>
                 <api:KEY2>{body_search['KEY2']}</api:KEY2>
                 <api:text>{self.search}</api:text>
                 <api:delivery_id>000000002</api:delivery_id>
                 <!--Optional:-->
                 <api:address_id>42716</api:address_id>
              </api:GetSearch>
           </soapenv:Body>
        </soapenv:Envelope>"""
        session = requests.Session()
        text = session.post(url=get_search, data=body, headers=headers).content
        stack_d = xmltodict.parse(text)
        self.result = []

        if stack_d['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns1:GetSearchResponse']['ns1:SearchResult'][
            'ns1:success'] == 'true':
            for part in \
                    stack_d['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns1:GetSearchResponse']['ns1:SearchResult'][
                        'ns1:PartsList'][
                        'ns1:Part']:
                try:
                    for stock in part['ns1:stocks']['ns1:stock']:
                        self.array_append(arr=self.result, section=part, warehouse=stock, orig='original')
                except:
                    try:
                        for cross_part in part['ns1:crosses']['ns1:Part']:
                            try:
                                for stock in cross_part['ns1:stocks']['ns1:stock']:
                                    self.array_append(arr=self.result, section=cross_part, warehouse=stock,
                                                      orig='analog')
                            except:
                                pass
                    except:
                        pass
        else:
            logger.error('no url block')

    def run(self):
        self.parse_page()
        logger.info(f' rossko: Получено {len(self.result)} элементов')
        return self.result


class Adeo:

    def __init__(self, search=''):
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='adeopro').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search

    def load_page(self):

        search_parameters = {
            'pn': self.search
        }
        headers = {'User-Agent': UserAgent().random}
        url = 'https://adeopro.ru/papi/pn'
        res = self.session.get(url, params=search_parameters, headers=headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'lxml')

        part_list_by_originality = {
            'original': [],
            'analog': []

        }
        try:
            for variant in soup.find_all('a'):  # перебор предложенных найденных брендов
                for origins in '3', '4':  # формирование параметров для парсинга каждой отдельной страницы
                    data = {
                            'kind': str(origins),
                            'pn': variant['href'].strip().split('&')[0][7:],
                            'brand': variant['href'].strip().split('&')[1][6:],
                            'limit_good_offers': '5'
                        }
                    response = self.session.get(
                        url='https://adeopro.ru/papi/price_part',
                        params=data,
                        headers={
                            'cookie': f"tary=rBIAAmEDuXiDF0RZA7tnAg ==; LegacyApp=ph1taf2gjne2mg008e1adh4st4c; "
                                      "REMEMBERME=TjJ4XENsaWVudEJ1bmRsZVxFbnRpdHlcVXNlcjpVbVZ1YjFCdWVrQjVZVzVrWlhndWNuVT06MTY2MDA2MDI2NToxYmVmOGFjMDQwZWM5YjQ5YzljYjg0ZTIxZWJhZTI0MDE4N2FhODc0Mjg1YWJmMTNhNGVkNWZiMWIzMGQ0ZWFk",
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.135 YaBrowser/21.6.3.757 Yowser/2.5 Safari/537.36',
                            'accept': 'application/json',
                        }
                    )
                    response.encoding = 'utf-8'

                if origins == '3':
                    part_list_by_originality['original'].append(response.json()['items'])
                else:
                    part_list_by_originality['analog'].append(response.json()['items'])

            return part_list_by_originality
        except:
            pass



    def parse_json(self, json_array):
        for origins in json_array:
            for origins_list in json_array[origins]:
                for block in origins_list:

                    url = f"https://adeopro.ru/pn?pn={block['pn_clean']}&brand={block['provider_original_name']}"
                    if not url:
                        logger.error('no href')

                    number = block['pn_clean']
                    if not number:
                        logger.error('no finis')

                    brand_name = block['provider_original_name']
                    if not brand_name:
                        logger.error('no brand name')

                    goods_name = block['pn_price_desc']
                    if not goods_name:
                        logger.error('no info')

                    price = int(block['cost_sale_format'].replace(" ", ""))
                    if not price:
                        logger.error('no price')

                    date = block['due_date_true']
                    if not date:
                        logger.error('no delivery date')

                    original = origins
                    if not original:
                        logger.error('no originality')

                    if block['pfid'] != None:
                        image_url = f'https://adeopro.ru/papi/partsphoto.php?nr={number}&tp=1&firm={brand_name}&index=0&snapshot=0'
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

    # def parse_image_url(self, nr, firm):
    #     """
    #     Осуществляет поиск URL-адреса изображения запчасти в спарсенном json файле.
    #     При наличии изображения возвращает его корректный URL адрес.
    #     При отсутстви изображения возвращает "no image".
    #     """
    #     headers = {'User-Agent': UserAgent().random}
    #     url = 'https://adeopro.ru/papi/partsphoto.php'
    #     params = {
    #         'nr': nr,
    #         'tp': '1',
    #         'firm': firm,
    #         'index': '0',
    #         'snapshot': '0',
    #     }
    #
    #     try:
    #         if id != None:
    #             page = self.session.get(url, headers=headers)
    #             page.encoding = 'utf8'
    #             soup = bs4.BeautifulSoup(page.text, 'lxml')
    #             return soup.find_all('img')[-1]['src']
    #         return 'no url'
    #     except:
    #         return 'no url'



    def run(self):
        text = self.load_page()
        if text:
            self.parse_json(text)
        logger.info(f'adeo.pro: Получено {len(self.result)} элементов')
        return self.result


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

    def load_page(self):
        search_parameters = {
            'page': 'price'
        }
        data = {
            'query': self.search,
            'm': 'any',
            'action': 'shop'
        }
        url = 'http://next-auto.pro/index.php?'
        headers = {
            'User-Agent': UserAgent().random
        }
        res = self.session.post(url, params=search_parameters, data=data, headers=headers, verify=False)
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        # парсинг ссылок на выдаваемые сайтом варианты по запрашиваемому артикулу
        url_to_check = [i['href'] for i in soup.find('td', id='content').find_all('a') if not i.has_attr('title')]
        return url_to_check

    def parse_page(self, text: str):
        headers = {
            'User-Agent': UserAgent().random
        }
        blocks_list = []
        for link in text:  # проверка ответа на наличие ссылок по данному артикулу
            params = {i.split('=')[0]: i.split('=')[1] for i in link.split('?')[1].split('&')}
            checked_res = self.session.get(url=link, params=params, headers=headers, verify=False)
            try:
                blocks_list.append(
                    [bs4.BeautifulSoup(checked_res.text, 'lxml').find_all('tr', class_='shop_move_out'), link])
            except:
                pass
        for blocks in blocks_list:
            for block in blocks[0]:
                if block:
                    self.parse_block(block=block, url=blocks[1])

    def parse_block(self, block, url):
        # block.content.decode('utf-8')
        if block.select('.results')[0].select('b'):
            original = 'original'
        else:
            original = 'analog'

        url = url
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
        text = self.load_page()
        self.parse_page(text=text)
        logger.info(f'next-auto: Получено {len(self.result)} элементов')
        return self.result

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

    def load_page(self):

        search_parameters = {
            'number': self.search,
            'maker_id': '',
            'excSubstitutes': '0',
            'excAnalogues': '0',
            'txtAddPrice': '0',
            'stores': '1',

        }
        headers = {'User-Agent': UserAgent().random}
        url = 'http://www.part-kom.ru/search/'
        res = self.session.get(url, params=search_parameters, headers=headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()

        for variant in res.json()['makers']:  # перебор предложенных найденных брендов
            link = 'http://www.part-kom.ru/search/'
            data = {
                'number': self.search,
                'maker_id': variant['id'],
                'excSubstitutes': '0',
                'excAnalogues': '0',
                'txtAddPrice': '0',
                'stores': '1'
            }
            response = self.session.get(url=link, params=data, headers={'User-Agent': UserAgent().random})
            response.encoding = 'utf-8'
            return response.json()

    def parse_json(self, json_array):
        origins = {
            'exact': 'original',
            'substitute': 'original_replacement',
            'analogue': 'analog'
        }


        for key in origins:
            try:
                for block in json_array[key]:
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

                        date = [d['deliveryCountDay'] for d in json_array['providers'] if
                                d['id'] == offer['source_provider_id']][0]
                        if not date and date != 0:
                            logger.error('no delivery date')

                        original = origins[key]
                        if not original:
                            logger.error('no originality')

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
            except:
                pass

    def run(self):
        self.parse_json(json_array=self.load_page())
        logger.info(f'part-kom: Получено {len(self.result)} элементов')
        return self.result


class AutoEuro:

    def __init__(self, search=''):
        self.session = requests.Session()
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='shop.autoeuro.ru').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search

    def load_page(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36'}
        url = f'https://shop.autoeuro.ru/main/search?text={self.search}&whs=&crosses=0&crosses=1'
        res = self.session.get(url, headers=headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        data_to_check = []
        parsed_urls = ['https://shop.autoeuro.ru/' + i['data-href'] for i in
                       soup.find('div', id='variants').find_all('span', class_='a_button go_search') if i]
        for parsed_url in parsed_urls:
            pus = parsed_url.split('=')
            data_to_check.append([parsed_url, {
                'mega_id': pus[1].split('&')[0],
                'maker': pus[2].split('&')[0],
                'code': pus[3].split('&')[0],
                'crosses': pus[-1],
            }])

        for link in data_to_check:  # перебор предложенных найденных брендов
            response = self.session.get(url='https://shop.autoeuro.ru/main/search', headers=headers, params=link[1],
                                        allow_redirects=True)
            return response.text

    def parse_page(self, text: str):
        soup = bs4.BeautifulSoup(text, 'lxml')
        for index in 1, 3:
            for blocks in soup.find_all(class_=f"search_maker_block proposals-{index}"):
                self.parse_block(blocks=blocks, original='original' if index == 1 else 'analog')

    def parse_block(self, blocks, original):
        month = {
            'января': '1',
            'февраля': '2',
            'марта': '3',
            'апреля': '4',
            'мая': '5',
            'июня': '6',
            'июля': '7',
            'августа': '8',
            'сентября': '9',
            'октября': '10',
            'ноября': '11',
            'декабря': '12'
        }
        blocks = blocks.select('tbody', class_='tb-all')
        for block in blocks:
            for el in block.select('tr', class_='row row-toggle row-all'):
                s = el.find('img', class_="order_basket_img")

                url = f"https://shop.autoeuro.ru/main/search?mega_id={s['data-mb_id']}"
                if not url:
                    logger.error('no href')

                number = s['data-code']
                if not number:
                    logger.error('no finis')

                brand_name = s['data-maker']
                if not brand_name:
                    logger.error('no brand name')

                goods_name = s['data-name']
                if not goods_name:
                    logger.error('no info')

                price = s['data-price']
                if not price:
                    logger.error('no price')

                date_row = s['data-delivery_time_string']
                if 'по' in date_row:
                    date_row = date_row.split('по')[1].split()
                    date_row[1] = [v for k, v in month.items() if str(k) in date_row[1]][0]
                    date_row = list(map(int, date_row))
                    date = int(
                        str(datetime.date(date_row[2], date_row[1], date_row[0]) - datetime.date.today()).split()[0])
                else:
                    date_row = date_row[2:].split()
                    date_row[1] = [v for k, v in month.items() if str(k) in date_row[1]][0]
                    date_row = list(map(int, date_row))
                    date = int(
                        str(datetime.date(date_row[2], date_row[1], date_row[0]) - datetime.date.today()).split()[0])

                if not date and date != 0:
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
        text = self.load_page()
        self.parse_page(text=text)
        logger.info(f'shop.autoeuro: Получено {len(self.result)} элементов')
        return self.result

class FavoritParts: # TODO: добавить поиск image_url

    def __init__(self, search=''):
        self.session = requests.Session()
        self.api_key = "01C96421-CAC2-11E3-9DC8-0050568E0E34"
        self.result = []
        self.search = search

    def load_brands(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36'}
        url = 'http://api.favorit-parts.ru/hs/hsprice/'
        res = self.session.get(url, params={
            'key': self.api_key,
            'number': self.search,
            'analogues': 'on'
        }, headers=headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        brands = [i['brand'] for i in res.json()['goods']]
        for brand in brands:  # перебор предложенных найденных брендов
            if brand:
                response = self.session.get(url, params={
                    'key': self.api_key,
                    'number': self.search,
                    'brand': brand,
                    'analogues': 'on'
                }, headers=headers, verify=False)
                return self.parse_json(response.json()['goods'][0])

    def warehouse_parse(self, text, original):
        for warehouse in text['warehouses']:
            brand_name = text['brand']

            number = text['number']

            goods_name = text['name']

            url = f"https://favorit-parts.ru/search/?number={number}"
            price = warehouse['price']
            date_row = list(map(int, warehouse['shipmentDate'].split('T')[0].split('-')))
            date = (datetime.date(*date_row) - datetime.date.today()).days
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


    def parse_json(self, text):
        try:
            if text['warehouses']:
                self.warehouse_parse(text=text, original='original')
        finally:
            try:
                for analog in text['analogues']:
                    if analog['warehouses'] != []:
                        self.warehouse_parse(text=analog, original='analog')
            except:
                pass
            pass



    def run(self):
        self.load_brands()
        logger.info(f'favorit-parts: Получено {len(self.result)} элементов')
        return self.result

class Exist():

    def __init__(self, search=''):
        self.session = requests.Session()
        self.z = Cookie.objects.filter(title='exist').values('value')[0]['value']
        self.result = []
        self.search = search

    def load_page(self):
        search_parameters = {
            'pcode': self.search
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
            'cookie': f"_z2={self.z}"
        }
        url = 'https://exist.ru/Price/'
        res = self.session.get(url, params=search_parameters, headers=headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        url_to_check = [f"https://exist.ru{i['href']}" for i in soup.find('ul', class_='catalogs').find_all('a')]
        return url_to_check

    def parse_page(self, text: str):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
            'cookie': f"_z2={self.z}"
        }
        blocks_list = []
        for link in text:  # проверка ответа на наличие ссылок по данному артикулу
            params = {i[0]: i[1] for i in link.split('?')[1].split('=')}
            checked_res = self.session.get(url=link, params=params, headers=headers, verify=False)
            soup = [i for i in bs4.BeautifulSoup(checked_res.text, 'lxml').find_all('script', type="text/javascript") if
                    'var _data' in str(i)]
            for script in soup:
                script.encoding = 'utf8'
                json_array = json.loads(str(script).split('var _data = ')[1].split('; var ')[0])
                self.parse_json(json_array=json_array)

    def parse_json(self, json_array):
        origins = {
            'Запрошенный артикул': 'original',
            'Другая упаковка': 'original',
            'Предложения по оригинальным производителям': 'original',
            'Предложения по заменителям': 'analog',
            'Артикулы с улучшенными характеристиками': 'original_replacement'
        }
        for block in json_array:
            for el in block['AggregatedParts']:

                url = f"https://exist.ru/Price/?pid={block['ProductIdEnc']}"
                if not url:
                    logger.error('no href')

                brand_name = block['CatalogName']
                if not brand_name:
                    logger.error('no brand name')

                number, image_url = self.parse_image_url(f"https://exist.ru{block['ProdUrl']}", brand_name)
                if not number:
                    logger.error('no finis')

                goods_name = block['Description']
                if not goods_name:
                    logger.error('no info')

                price = float(el['price'])
                if not price:
                    logger.error('no price')

                date = el['days']
                if not date and date != 0:
                    logger.error('no delivery date')

                if block['BlockText'] == 'Любимые бренды':
                    continue
                original = origins[block['BlockText']]
                if not original:
                    logger.error('no originality')

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

    def parse_image_url(self, url, brand):
        """
        Осуществляет поиск URL-адреса изображения запчасти в спарсенном json файле.
        При наличии изображения возвращает его корректный URL адрес.
        При отсутстви изображения возвращает "no image".
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
        }
        url = url
        try:
            page = self.session.get(url, headers=headers)
            page.encoding = 'utf8'
            soup = bs4.BeautifulSoup(page.text, 'lxml')
            finis = soup.find('h1', class_='fn identifier').find('a', id='ctl00_b_ctl00_hlMainLink').text.strip(
                f"{brand} ").replace(' ', '')
            img_url = f"https:{soup.find('div', class_='photo').find('a')['href']}"
            return finis, img_url
        except:
            page = self.session.get(url, headers=headers)
            page.encoding = 'utf8'
            soup = bs4.BeautifulSoup(page.text, 'lxml')
            finis = soup.find('h1', class_='fn identifier').find('a', id='ctl00_b_ctl00_hlMainLink').text.strip(
                f"{brand} ").replace(' ', '')
            return finis, "no url"

    def run(self):
        text = self.load_page()
        self.parse_page(text)
        logger.info(f'exist: Получено {len(self.result)} элементов')
        return self.result

class M_Parts():

    def __init__(self, search=''):
        self.session = requests.Session()
        self.result = []
        self.search = search
        self.login = Cookie.objects.filter(title='m-parts.ru')[0].user_login
        self.md5_pass = hashlib.md5(Cookie.objects.filter(title='m-parts.ru')[0].user_password.encode()).hexdigest()

    def load_json(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
        }
        url_to_search_brand = f"http://v01.ru/api/devinsight/search/brands/?userlogin={self.login}&userpsw={self.md5_pass}&number={self.search}&useOnlineStocks=1"
        first_res = self.session.get(url_to_search_brand, headers=headers, verify=False)
        first_res.encoding = 'utf8'
        first_res.raise_for_status()
        first_res = first_res.json()
        for variant in first_res:
            brand = first_res[variant]['brand']
            number = first_res[variant]['number']
            url_to_search_articles = f"http://v01.ru/api/devinsight/search/articles/?userlogin={self.login}&userpsw={self.md5_pass}&number={number}&brand={brand}"
            second_res = self.session.get(url_to_search_articles, headers=headers, verify=False)
            second_res.encoding = 'utf8'
            second_res.raise_for_status()
            second_res = second_res.json()
            return second_res, brand, number

    def parse_json(self, json_array, brand, finis):

        for el in json_array:

            brand_name = el['brand']
            if not brand_name:
                logger.error('no brand name')

            number = el['number']
            if not number:
                logger.error('no finis')

            original = 'original' if (brand_name == brand) and (finis == number) else 'analog'
            if not original:
                logger.error('no originality')

            url = f"http://v01.ru/auto/search/{number}/"
            if not url:
                logger.error('no href')

            goods_name = el['description']
            if not goods_name:
                logger.error('no info')

            price = float(el['price'])
            if not price:
                logger.error('no price')

            date = datetime.timedelta(hours=el['deliveryPeriod']).days
            if not date and date != 0:
                logger.error('no delivery date')

            image_url = self.parse_image_url(brand_name, number)

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
        """
        Осуществляет поиск URL-адреса изображения запчасти в спарсенном json файле.
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 YaBrowser/21.8.0.1379 Yowser/2.5 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        res = self.session.post(url=url, headers=headers, data=js, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        return 'http://v01.ru/' + res.json()['FOUND'][f'{brand_name}_{number}'][0]['DETAIL'] if res.json()[
            'FOUND'] else 'no url'

    def run(self):
        json_array, brand, number = self.load_json()
        self.parse_json(json_array=json_array, brand=brand, finis=number)
        logger.info(f'm-parts: Получено {len(self.result)} элементов')
        return self.result

class STParts():

    def __init__(self, search=''):
        self.session = requests.Session()
        self.result = []
        cookies_dict = [
            {'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in Cookie.objects.filter(title='stparts').all()
        ]
        for cookies in cookies_dict:
            self.session.cookies.set(**cookies)
        self.result = []
        self.search = search
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
        }

    def load_page(self):
        url_to_search_brand = f"https://stparts.ru/search"
        res = self.session.get(url_to_search_brand, params={'pcode': self.search}, headers=self.headers, verify=False)
        res.encoding = 'utf8'
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        return soup.find_all('tr', class_="startSearching")

    def parse_page(self, text):
        for variant in text:
            link = variant['data-link']
            if link:
                res = self.session.get(url=f"https://stparts.ru{link}", headers=self.headers)
                res.encoding = 'utf-8'
                res.raise_for_status()
                page = bs4.BeautifulSoup(res.text, 'lxml')
                blocks = page.find('table', id='searchResultsTable').find('tbody').find_all('tr', class_='resultTr2')
                try:
                    data_block = page.noindex.find('div', id="tplData")
                    search_brand = data_block['searchbrand']
                    search_number = data_block['searchnumber']
                    reseller_id = data_block['resellerid']
                    customer_id_for_search = data_block['customeridforsearch']
                    customer_id_for_price = data_block['customeridforprice']
                    extra_url = f"https://stparts.ru/searchResults?action=showMoreAnalogs&searchBrand={search_brand}&" \
                                f"searchNumber={search_number}&resellerId={reseller_id}&" \
                                f"customerIdForSearch={customer_id_for_search}&customerIdForPrice={customer_id_for_price}&enc="
                    extra_page = self.session.get(url=extra_url, headers={
                        'referer': f'https://stparts.ru/search/{search_brand}/{search_number}',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',

                    })
                    self.parse_block(bs4.BeautifulSoup(extra_page.text, 'lxml').find_all('tr', class_='resultTr2'))
                except:
                    print('Дополнительный блок отсутствует')
                self.parse_block(blocks)

    def parse_block(self, block):

        for el in block:
            try:
                if not el['data-availability']:
                    continue
                quality = el['data-is-quality-brand'] or 0
                is_analog = el['data-is-analog'] or 0
                if quality == 0 and is_analog == 0:
                    original = 'original'
                if quality == 1 and is_analog == 1:
                    original = 'original_replacement'
                else:
                    original = 'analog'
                if not original:
                    logger.error('no originality')

                url = f"https://stparts.ru{el.find('a', class_='searchInfoLink')['href']}"
                if not url:
                    logger.error('no href')


                brand_number_img_data = el.find('img', class_='searchResultImg')
                brand_name = brand_number_img_data['data-brand']
                if not brand_name:
                    logger.error('no brand name')

                number = brand_number_img_data['data-code']
                if not number:
                    logger.error('no finis')

                goods_name = el.find('td', class_='resultDescription').text.strip()
                if not goods_name:
                    logger.error('no info')

                date = el.find('td', class_='resultDeadline').text.split()
                if date:
                    date = date[2]
                else:
                    logger.error('no delivery date')

                price = el.find('td', class_='resultPrice').text.strip()
                if price:
                    price = float(price.split(' руб')[0].replace(' ', '').replace(',', '.'))
                else:
                    logger.error('no price')

                no_img = '//pubimg.4mycar.ru/images/05ec2886842e3204c84e1560b0b40a7964.png'
                image_url = f"https:{brand_number_img_data['src']}" if brand_number_img_data['src'] != no_img else 'no url'
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
            except:
                continue

    def run(self):
        text = self.load_page()
        self.parse_page(text=text)
        logger.info(f'stparts: Получено {len(self.result)} элементов')
        return self.result