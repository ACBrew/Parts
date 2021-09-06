from django.db import models


class Cookie(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField('Title of site', max_length=100)
    link = models.CharField('Link', max_length=150)
    user_login = models.CharField('Login', max_length=50)
    user_password = models.CharField('Password', max_length=50)
    domain = models.CharField('Session domain', max_length=250)
    name = models.CharField('Session name', max_length=250)
    value = models.CharField('Session value', max_length=250)
    path = models.CharField('Session path', max_length=250)


class Xhr(models.Model):
    title = models.CharField('Title of site', max_length=100)
    remember_me = models.CharField('REMEMBER_ME from headers', max_length=200)
    legacyapp = models.CharField('LegacyApp from headers', max_length=200)
