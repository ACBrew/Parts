import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import xmltodict
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from concurrent.futures import ThreadPoolExecutor
import json

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(':::')


class Rossko:

    def __init__(self, search=''):
        self.search = search
        self.result = []
        self.key_1 = 'cf947057674a3f96aba069db6e0b1e73'
        self.key_2 = '9379490cbcde554d90404df9307c0444'
        self.address_id = '42716'

    def get_all_offers(self):
        """Осуществляет запрос к SOAP API и возвращает xml содеражащий список запчастей или пустой список в случае
        ошибки"""

        get_search = 'http://api.rossko.ru/service/v2.1/GetSearch'
        headers = {'content-type': 'application/soap+xml; charset=utf-8'}

        body = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:api="http://api.rossko.ru/">
           <soapenv:Header/>
           <soapenv:Body>
              <api:GetSearch>
                 <api:KEY1>{self.key_1}</api:KEY1>
                 <api:KEY2>{self.key_2}</api:KEY2>
                 <api:text>{self.search}</api:text>
                 <api:delivery_id>000000002</api:delivery_id>
                 <!--Optional:-->
                 <api:address_id>{self.address_id}</api:address_id>
              </api:GetSearch>
           </soapenv:Body>
        </soapenv:Envelope>"""
        session = requests.Session()
        text = session.post(url=get_search, data=body, headers=headers).content
        stack_d = json.loads(json.dumps(xmltodict.parse(text)))
        stack_d = stack_d['SOAP-ENV:Envelope']['SOAP-ENV:Body']['ns1:GetSearchResponse']['ns1:SearchResult']
        if stack_d['ns1:success'] == 'true':
            return stack_d['ns1:PartsList']['ns1:Part']
        else:
            return []

    def get_offers(self, xml_of_offers):
        if isinstance(xml_of_offers, list):
            for part in xml_of_offers:
                if part.get('ns1:stocks', False):
                    self.get_part(part, 'original')
                    continue
                if part.get('ns1:crosses', False):
                    if isinstance(part['ns1:crosses']['ns1:Part'], list):
                        for el in part['ns1:crosses']['ns1:Part']:
                            self.get_part(el, 'analog')
                    else:
                        self.get_part(part['ns1:crosses']['ns1:Part'], 'analog')
        else:
            if xml_of_offers.get('ns1:stocks', False):
                self.get_part(xml_of_offers, 'original')
            if xml_of_offers.get('ns1:crosses', False):
                if isinstance(xml_of_offers['ns1:crosses']['ns1:Part'], list):
                    for part in xml_of_offers['ns1:crosses']['ns1:Part']:
                        self.get_part(part, 'analog')
                else:
                    self.get_part(xml_of_offers['ns1:crosses']['ns1:Part'], 'analog')
            return

    def get_part(self, section, originality):
        """Добавляет информацию о детали в список self.result"""
        if isinstance(section['ns1:stocks']['ns1:stock'], list):
            for stock in section['ns1:stocks']['ns1:stock']:
                self.result.append(self.get_part_info(section, originality) | self.get_stock(stock))
        else:
            d = self.get_part_info(section, originality)
            self.result.append(d | self.get_stock(section['ns1:stocks']['ns1:stock']))

    def get_part_info(self, section, originality):
        return {'originality': originality,
                'url': 'https://penza.rossko.ru/product?text=' + section['ns1:guid'],
                'brand_name': section['ns1:brand'],
                'finis': section['ns1:partnumber'],
                'goods_name': section['ns1:name'] or 'Описание отсутствует',
                'image_url': 'no url'}

    def get_stock(self, stock):
        """Возвращает информацию по складу в виде словаря"""
        return {'delivery_date': stock['ns1:delivery'], 'price': stock['ns1:price']}

    def run(self):      # TODO: возможно! добавить многопоточность
        xml_of_offers = self.get_all_offers()
        if xml_of_offers:
            self.get_offers(xml_of_offers)
        logger.info(f'rossko: Получено {len(self.result)} элементов')
        return self.result
