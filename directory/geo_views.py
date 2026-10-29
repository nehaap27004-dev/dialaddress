from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import geo
from .models import Business, Category, City, Country
from .seo import breadcrumb_jsonld, to_json
from .views import SORTS, _cities, _page_context

LINK_LIMIT = 40


# ---------- helpers ----------
def _lowercase_redirect(request):
    """/Oman/Muscat/ -> /oman/muscat/ (one address per page)."""
    if request.path != request.path.lower():
        qs = request.META.get("QUERY_STRING")
        return redirect(request.path.lower() + (f"?{qs}" if qs else ""), permanent=True)
    return None


def _businesses(country=None, city=None, category=None):
    qs = Business.objects.filter(is_active=True)
    if city is not None:
        qs = qs.filter(city=city)
    elif country is not None:
        qs = qs.filter(city__country=country)
    if category is not None:
        qs = qs.filter(Q(category=category) | Q(subcategory=category))
    return qs.select_related("category", "city").order_by(*SORTS["relevance"])


def _cities_with_businesses(country, category=None):
    biz = Q(businesses__is_active=True)
    if category is not None:
        biz &= (Q(businesses__category=category) | Q(businesses__subcategory=category))
    return (City.objects.filter(country=country).filter(biz)
            .select_related("country").distinct().order_by("name")[:LINK_LIMIT])


def _categories_with_businesses(country=None, city=None, parent=None, exclude=None):
    main = Q(businesses__is_active=True)
    sub = Q(sub_businesses__is_active=True)
    if city is not None:
        main &= Q(businesses__city=city)
        sub &= Q(sub_businesses__city=city)
    elif country is not None:
        main &= Q(businesses__city__country=country)
        sub &= Q(sub_businesses__city__country=country)
    qs = Category.objects.filter(main | sub)
    if parent is not None:
        qs = qs.filter(parent=parent)
    if exclude is not None:
        qs = qs.exclude(pk=exclude.pk)
    return qs.distinct().order_by("order", "name")[:LINK_LIMIT]


def _cat_link(category, country, city=None):
    return geo.city_category_url(city, category) if city else geo.category_url(category, country)


def _category_crumbs(category, country, city=None):
    crumbs = [("Home", reverse("home")), (country.name, geo.country_url(country))]
    if city:
        crumbs.append((city.name, geo.city_url(city)))
    if category.parent_id:
        crumbs.append((category.parent.name, _cat_link(category.parent, country, city)))
    crumbs.append((category.name, _cat_link(category, country, city)))
    return crumbs


def _render(request, *, heading, intro, crumbs, businesses, path, extra):
    ctx = _page_context(request, businesses)          # 404 on a bad ?page=
    page = ctx["page_obj"].number
    ctx.update({
        "heading": heading,
        "intro": intro,
        "crumbs": crumbs,
        "breadcrumb_jsonld": to_json(breadcrumb_jsonld(request, crumbs)),
        "canonical": request.build_absolute_uri(path + (f"?page={page}" if page > 1 else "")),
        "cities": _cities(),          # for the search box
        "q": "",
        "selected_city": "",
    })
    ctx.update(extra)
    return render(request, "directory/geo_listing.html", ctx)


# ---------- page builders ----------
def _country_response(request, country):
    sections = [
        (f"Cities in {country.name}",
         [(c.name, geo.city_url(c)) for c in _cities_with_businesses(country)]),
        ("Popular categories",
         [(c.name, geo.category_url(c, country)) for c in _categories_with_businesses(country=country)]),
    ]
    return _render(
        request,
        heading=f"Businesses in {country.name}",
        intro=f"Browse local businesses across {country.name}. Compare ratings, see photos and opening hours, then call or message them directly.",
        crumbs=[("Home", reverse("home")), (country.name, geo.country_url(country))],
        businesses=_businesses(country=country),
        path=geo.country_url(country),
        extra={"country": country, "link_sections": sections},
    )


def _city_response(request, country, city):
    sections = [(f"Popular categories in {city.name}",
                 [(c.name, geo.city_category_url(city, c)) for c in _categories_with_businesses(city=city)])]
    return _render(
        request,
        heading=f"Businesses in {city.name}",
        intro=f"Browse local businesses in {city.name}, {country.name}. Compare ratings, see photos and opening hours, then call or message them directly.",
        crumbs=[("Home", reverse("home")), (country.name, geo.country_url(country)),
                (city.name, geo.city_url(city))],
        businesses=_businesses(city=city),
        path=geo.city_url(city),
        extra={"country": country, "city": city, "selected_city": str(city.pk), "link_sections": sections},
    )


def _category_response(request, country, category):
    sections = [
        (f"Types of {category.name}",
         [(c.name, geo.category_url(c, country))
          for c in _categories_with_businesses(country=country, parent=category)]),
        (f"{category.name} by city",
         [(c.name, geo.city_category_url(c, category)) for c in _cities_with_businesses(country, category)]),
    ]
    return _render(
        request,
        heading=f"{category.name} in {country.name}",
        intro=f"Find {category.name} businesses in {country.name}. Compare ratings, see photos and opening hours, then call or message them directly.",
        crumbs=_category_crumbs(category, country),
        businesses=_businesses(country=country, category=category),
        path=geo.category_url(category, country),
        extra={"country": country, "category": category, "link_sections": sections},
    )


def _city_category_response(request, country, city, category):
    sections = [
        (f"Types of {category.name} in {city.name}",
         [(c.name, geo.city_category_url(city, c))
          for c in _categories_with_businesses(city=city, parent=category)]),
        (f"Other categories in {city.name}",
         [(c.name, geo.city_category_url(city, c))
          for c in _categories_with_businesses(city=city, exclude=category)]),
        (f"{category.name} in other cities",
         [(c.name, geo.city_category_url(c, category))
          for c in _cities_with_businesses(country, category) if c.pk != city.pk]),
    ]
    return _render(
        request,
        heading=f"{category.name} in {city.name}",
        intro=f"Find {category.name} in {city.name}, {country.name}. Compare ratings, see photos and opening hours, then call or message them directly.",
        crumbs=_category_crumbs(category, country, city),
        businesses=_businesses(city=city, category=category),
        path=geo.city_category_url(city, category),
        extra={"country": country, "city": city, "category": category,
               "selected_city": str(city.pk), "link_sections": sections},
    )


# ---------- the views the URLs point to ----------
def country_page(request, country_slug):
    """/oman/"""
    resp = _lowercase_redirect(request)
    if resp:
        return resp
    country = get_object_or_404(Country, slug=country_slug)
    return _country_response(request, country)


def segment_page(request, country_slug, segment):
    """/oman/muscat/ (a city) or /oman/car-workshops/ (a category)."""
    resp = _lowercase_redirect(request)
    if resp:
        return resp
    country = get_object_or_404(Country, slug=country_slug)

    city = City.objects.select_related("country").filter(country=country, slug=segment).first()
    if city:
        return _city_response(request, country, city)

    category = Category.objects.select_related("parent").filter(slug=segment).first()
    if category:
        return _category_response(request, country, category)

    # a real city, but under the wrong country: send them to the right address
    elsewhere = City.objects.select_related("country").filter(slug=segment, country__isnull=False).first()
    if elsewhere:
        return redirect(geo.city_url(elsewhere), permanent=True)
    raise Http404


def city_category_page(request, country_slug, city_slug, category_slug):
    """/oman/barka/car-workshops/ (also services and products, which are subcategories)."""
    resp = _lowercase_redirect(request)
    if resp:
        return resp
    country = get_object_or_404(Country, slug=country_slug)
    city = City.objects.select_related("country").filter(slug=city_slug).first()
    if city is None:
        raise Http404
    category = get_object_or_404(Category.objects.select_related("parent"), slug=category_slug)
    if city.country_id != country.id:
        if city.country_id:
            return redirect(geo.city_category_url(city, category), permanent=True)
        raise Http404
    return _city_category_response(request, country, city, category)