import bs4
from django.shortcuts import render
import requests
from .forms import PostForm
from .models import Cookie, Xhr
from django.shortcuts import redirect
import fake_useragent
import json


def index(request):
    data = {
        'title': 'Введите Ваш запрос',
        'message': None
    }
    return render(request, 'main/index.html', data)


def profile_cookies(request):
    """Ввод данных для авторизации на сайте и сохранения сессии для дальнейшго парсинга"""
    sites = {
        'ixora-auto': 'ixora-auto',
        'adeopro': 'adeopro',
        'next-auto': 'next-auto',
        'part-kom': 'part-kom',
        'shop.autoeuro': 'shop.autoeuro',
        'm-parts': 'm-parts',
        'stparts': 'stparts',
        'berg': 'berg'

    }
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            session = requests.Session()
            user = fake_useragent.UserAgent().random
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 YaBrowser/21.6.4.693 Yowser/2.5 Safari/537.36',
            }
            site_dict = {
                'ixora-auto': {
                    'UserName': post.user_login,
                    'Password': post.user_password
                },
                'adeopro': {
                    'UserName': post.user_login,
                    'Password': post.user_password
                },
                'next-auto': {
                    'login': post.user_login,
                    'pass': post.user_password
                },
                'part-kom': {
                    'txtLogin': post.user_login,
                    'txtPassword': post.user_password
                },
                'shop.autoeuro': {
                    'login': 'login',
                    'username': post.user_login,
                    'password': post.user_password,
                    'remember': 'checked'
                },
                'm-parts': {
                    'login': post.user_login,
                    'pass': post.user_password
                },
                'stparts': {
                    'login': post.user_login,
                    'pass': post.user_password
                },
                'berg': {
                    '_target_path': "",
                    '_username': post.user_login,
                    '_password': post.user_password,
                    '_submit': "Войти"
                }}
            if post.title == 'next-auto':
                session.post(post.link, params={'page': 'news'}, data=site_dict['next-auto'],
                             headers=headers)
            elif post.title == 'adeopro':  # парсинг данных для xhr запросов на данный домен
                adeo_headers = {
                    'Content-Type': 'application/json;charset=utf-8',
                    'user-agent': user,
                }
                data = {"username": post.user_login, "password": post.user_password}

                token = session.post(
                    url='https://adeopro.ru/api/auth/signin',
                    data=json.dumps(data),
                    headers=adeo_headers).json()['accessToken']

                data_from_headers = session.post(
                    url='https://adeopro.ru/papi/jwtlogin',
                    params={'token': token},
                    headers=adeo_headers).headers

                try:
                    Xhr.objects.filter(title=post.title).all().delete()
                    Xhr.objects.create(
                        title='adeopro',
                        remember_me=data_from_headers['Set-Cookie'].split('REMEMBERME=')[1].split(';')[0],
                        legacyapp=data_from_headers['Set-Cookie'].split('LegacyApp=')[1].split(';')[0]
                    )
                    Xhr.save()
                except:
                    pass
            elif post.title == 'm-parts':       #TODO: реализовать принцип DRY
                cookies_dict = [
                    {'title': post.title,
                     'link': post.link,
                     'user_login': post.user_login,
                     'user_password': post.user_password,
                     'domain': 'v01.ru',
                     'name': 'v01.ru',
                     'path': 'v01.ru',
                     'value': 'v01.ru'}
                ]
            elif post.title == 'berg':
                soup = bs4.BeautifulSoup(session.get(post.link, headers=headers).text, 'lxml')
                site_dict[post.title]['_csrf_token'] = soup.find_all('form', action="/login_check")[1].input['value']
                session.post(post.link, data=site_dict[post.title], headers=headers)
                cookies_dict = [
                    {'title': post.title,
                     'link': post.link,
                     'user_login': post.user_login,
                     'user_password': post.user_password,
                     'domain': key.domain,
                     'name': key.name,
                     'path': key.path,
                     'value': key.value}
                    for key in session.cookies
                ]
                print(cookies_dict)
            else:
                session.post(post.link, data=site_dict[post.title], headers=headers)
                cookies_dict = [
                    {'title': post.title,
                     'link': post.link,
                     'user_login': post.user_login,
                     'user_password': post.user_password,
                     'domain': key.domain,
                     'name': key.name,
                     'path': key.path,
                     'value': key.value}
                    for key in session.cookies
                ]

            try:
                Cookie.objects.filter(title=post.title).all().delete()
                Cookie.objects.bulk_create(Cookie(**val) for val in cookies_dict)
            except:
                pass

            post.save()
            Cookie.objects.filter(domain='').all().delete()

            return redirect('profile_cookies')

    else:
        form = PostForm()
        context = {
            'form': form,
            'sites': sites
        }
    return render(request, 'main/profile.html', context)
