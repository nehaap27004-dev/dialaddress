from django.conf import settings
from django.db.models import Count, Q
from django.urls import reverse

from .models import Country


def country_url(country):
    return reverse("geo_country", args=[country.slug])


def city_url(city):
    """/oman/muscat/ (falls back to search if the city has no country)."""
    if city.country_id:
        return reverse("geo_city", args=[city.country.slug, city.slug])
    return f"{reverse('search')}?city={city.pk}"


def category_url(category, country=None):
    """/oman/car-workshops/"""
    if country is None:
        return f"{reverse('search')}?category={category.slug}"
    return reverse("geo_category", args=[country.slug, category.slug])


def city_category_url(city, category):
    """/oman/barka/car-workshops/"""
    if city.country_id:
        return reverse("geo_city_category", args=[city.country.slug, city.slug, category.slug])
    return f"{reverse('search')}?city={city.pk}&category={category.slug}"


def default_country(category=None):
    """
    The country used when a link has no location (homepage icons, old URLs).
    Set DEFAULT_COUNTRY_SLUG in settings.py to force one; otherwise it is the
    country with the most live businesses (in the category, if one is given).
    """
    slug = getattr(settings, "DEFAULT_COUNTRY_SLUG", "")
    if slug:
        forced = Country.objects.filter(slug=slug).first()
        if forced:
            return forced
    biz = Q(cities__businesses__is_active=True)
    if category is not None:
        biz &= (Q(cities__businesses__category=category) | Q(cities__businesses__subcategory=category))
    return (Country.objects
            .annotate(n=Count("cities__businesses", filter=biz, distinct=True))
            .order_by("-n", "name").first())