from django import template

register = template.Library()


@register.filter
def create_range(value, start_index=0):
    return range(start_index, value + start_index)


@register.filter
def price_block(lst, val):
    return [[i[4], i[5], i[7]] for i in lst if i[2] == val]

@register.filter
def price_block_obj(lst, val):
    return [[i.delivery_date, i.price, i.url] for i in lst if i.finis == val]
