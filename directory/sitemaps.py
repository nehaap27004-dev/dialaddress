from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse

from .models import Business, Category, City


class StaticSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return ["home", "photos"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return (
            Category.objects.filter(
                Q(businesses__is_active=True) | Q(sub_businesses__is_active=True)
            )
            .distinct()
            .order_by("id")
        )

    def location(self, obj):
        return reverse("category_page", args=[obj.slug])


class CitySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return City.objects.filter(businesses__is_active=True).distinct().order_by("id")

    def location(self, obj):
        return reverse("city_page", args=[obj.slug])


class BusinessSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Business.objects.filter(is_active=True).order_by("id")  # live listings only

    def location(self, obj):
        return reverse("business_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at