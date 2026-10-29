from django import template

from .. import geo

register = template.Library()


@register.simple_tag
def country_link(country):
    return geo.country_url(country)


@register.simple_tag
def city_link(city):
    return geo.city_url(city)


@register.simple_tag
def category_link(category, country=None):
    return geo.category_url(category, country)


@register.simple_tag
def city_category_link(city, category):
    return geo.city_category_url(city, category)