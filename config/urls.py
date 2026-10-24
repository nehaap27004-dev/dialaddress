from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from directory.sitemaps import BusinessSitemap, CategorySitemap, CitySitemap, StaticSitemap
from directory.views import robots_txt

sitemaps = {
    "static": StaticSitemap,
    "categories": CategorySitemap,
    "cities": CitySitemap,
    "businesses": BusinessSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}),
    path("robots.txt", robots_txt),
    path("", include("directory.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)