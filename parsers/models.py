from django.db import models


class Parts(models.Model):
    id = models.AutoField(primary_key=True)
    originality = models.CharField('Оригинальность', max_length=50)
    brand_name = models.CharField('Бренд', max_length=50)
    finis = models.CharField('Артикул', max_length=50)
    goods_name = models.CharField('Описание', default="", max_length=150)
    delivery_date = models.CharField('Срок доставки', max_length=20)
    price = models.DecimalField('Цена', max_digits=9, decimal_places=2)
    url = models.CharField('URL', max_length=50)
    image_url = models.CharField('URL изображения', max_length=50)

    def __str__(self):
        return self.originality

    class Meta:
        verbose_name = 'Запчасть'
        verbose_name_plural = 'Запчасти'
