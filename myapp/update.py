from main.models import Cookie
import os
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options


class UpdateCookies():

    def part_kom_update(self):
        session = requests.Session()
        qset = Cookie.objects.filter(title='part-kom')
        link = qset.values('link')[0]['link']
        params = {'part-kom': {
            'txtLogin': qset.values('user_login')[0]['user_login'],
            'txtPassword': qset.values('user_password')[0]['user_password']}}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36'
        }
        response = session.post(link, data=params['part-kom'], headers=headers)
        cookies_dict = [
            {'title': 'part-kom',
             'link': link,
             'user_login': params['part-kom']['txtLogin'],
             'user_password': params['part-kom']['txtPassword'],
             'domain': key.domain,
             'name': key.name,
             'path': key.path,
             'value': key.value}
            for key in response.cookies
        ]

        try:
            Cookie.objects.filter(title='part-kom').all().delete()
            Cookie.objects.bulk_create(Cookie(**val) for val in cookies_dict)
        except:
            pass
        Cookie.objects.filter(domain='').all().delete()
        print(f'-*-*- part-kom updated')

    def init_driver(self):
        EXE_PATH = r'D:\Python\Projects\MyProject\myapp\main\static\main\selenium\geckodriver.exe'  # EXE_PATH это путь до ранее загруженного нами файла chromedriver.exe
        opts = Options()
        opts.set_headless()
        assert opts.headless  # без графического интерфейса.
        driver = webdriver.Firefox(executable_path=EXE_PATH, options=opts)
        # driver = webdriver.Firefox()

        driver.wait = WebDriverWait(driver, 10)
        return driver

    def lookup(self, driver):
        driver.get('https://exist.ru/')
        try:
            button = driver.wait.until(EC.presence_of_element_located((By.ID, "pnlLogin")))
            button.click()
            window = driver.wait.until(EC.presence_of_element_located((By.ID, "guestForm")))
            driver.find_element_by_id("login").send_keys('79379151465')
            password = driver.find_element_by_id("pass").send_keys('0509romm')
            driver.find_element_by_id("btnLogin").click()

        except TimeoutException:
            print("Box or Button not found in exist.ru")

    def exist_update(self):
        driver = self.init_driver()
        self.lookup(driver)
        time.sleep(5)
        # print(driver.get_cookies())
        for _ in driver.get_cookies():
            if _['name'] == '_z2':
                cookies_dict = [
                    {'title': 'exist',
                     'link': 'https://exist.ru/',
                     'user_login': '79379151465',
                     'user_password': '0509romm',
                     'domain': 'https://exist.ru/',
                     'name': '_z2',
                     'path': '/',
                     'value': f"{_['value']}"}
                ]

                try:
                    Cookie.objects.filter(title='exist').all().delete()
                    Cookie.objects.bulk_create(Cookie(**val) for val in cookies_dict)
                except:
                    pass
        driver.quit()
        print(f'-*-*- exist updated')

    def run(self):
        driver = self.init_driver()
        print('-*-*- драйвер инициализирован')
        self.lookup(driver)
        print('-*-*- авторизация пройдена')
        time.sleep(1)
        driver.quit()
        self.exist_update()
        self.part_kom_update()
        print('>>>>>    UPDATE COMPLETE    <<<<<')


