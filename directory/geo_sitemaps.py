from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from . import geo
from .models import Business, City, Country


def _rows():
    return (Business.objects.filter(is_active=True, city__country__isnull=False)
            .values_list("city__country__slug", "city__slug", "category__slug", "subcategory__slug")
            .distinct())


class _Geo(Sitemap):
    changefreq = "weekly"
    priority = 0.7


class CountrySitemap(_Geo):
    def items(self):
        return Country.objects.filter(cities__businesses__is_active=True).distinct()

    def location(self, obj):
        return geo.country_url(obj)


class CitySitemap(_Geo):
    def items(self):
        return (City.objects.filter(country__isnull=False, businesses__is_active=True)
                .select_related("country").distinct())

    def location(self, obj):
        return geo.city_url(obj)


class CategorySitemap(_Geo):
    def items(self):
        found = set()
        for country, _city, cat, sub in _rows():
            found.add((country, cat))
            if sub:
                found.add((country, sub))
        return sorted(found)

    def location(self, item):
        return reverse("geo_category", args=item)


class CityCategorySitemap(_Geo):
    def items(self):
        found = set()
        for country, city, cat, sub in _rows():
            found.add((country, city, cat))
            if sub:
                found.add((country, city, sub))
        return sorted(found)

    def location(self, item):
        return reverse("geo_city_category", args=item)