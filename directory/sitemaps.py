from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from . import geo
from .models import Business, City, Country


class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["home", "photos"]

    def location(self, item):
        return reverse(item)


def _rows():
    """(country, city, category, subcategory) slugs of every live business that has a country."""
    return (
        Business.objects.filter(is_active=True, city__country__isnull=False)
        .order_by()  # clear the model's default ordering so distinct() works
        .values_list("city__country__slug", "city__slug", "category__slug", "subcategory__slug")
        .distinct()
    )


class CountrySitemap(Sitemap):
    """/oman/"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Country.objects.filter(cities__businesses__is_active=True).distinct().order_by("id")

    def location(self, obj):
        return geo.country_url(obj)


class CitySitemap(Sitemap):
    """/oman/muscat/"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return (
            City.objects.filter(country__isnull=False, businesses__is_active=True)
            .select_related("country")
            .distinct()
            .order_by("id")
        )

    def location(self, obj):
        return geo.city_url(obj)


class CategorySitemap(Sitemap):
    """/oman/car-workshops/ (subcategories such as /oman/ac-repair/ too)"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        found = set()
        for country, _city, cat, sub in _rows():
            found.add((country, cat))
            if sub:
                found.add((country, sub))
        return sorted(found)

    def location(self, item):
        return reverse("geo_category", args=item)


class CityCategorySitemap(Sitemap):
    """/oman/barka/car-workshops/ (subcategories such as /oman/barka/ac-repair/ too)"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        found = set()
        for country, city, cat, sub in _rows():
            found.add((country, city, cat))
            if sub:
                found.add((country, city, sub))
        return sorted(found)

    def location(self, item):
        return reverse("geo_city_category", args=item)


class BusinessSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Business.objects.filter(is_active=True).order_by("id")  # live listings only

    def location(self, obj):
        return reverse("business_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at