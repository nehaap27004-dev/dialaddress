import json

from django.urls import reverse

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Category slug -> the closest schema.org business type
SCHEMA_TYPES = {
    "restaurants": "Restaurant",
    "hospitals": "Hospital",
    "automobile": "AutoDealer",
    "banking-finance": "BankOrCreditUnion",
    "electronics": "ElectronicsStore",
    "jewellery": "JewelryStore",
}


def clean_text(text, limit=155):
    """One line of plain text, cut at a word boundary."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",.;: ") + "…"


def to_json(data):
    """JSON for a <script type="application/ld+json"> tag (safe against </script>)."""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def business_jsonld(request, b, photos, hours, reviews):
    def absolute(path):
        return request.build_absolute_uri(path)

    url = absolute(reverse("business_detail", args=[b.slug]))
    data = {
        "@context": "https://schema.org",
        "@type": SCHEMA_TYPES.get(b.category.slug, "LocalBusiness"),
        "@id": url + "#business",
        "name": b.name,
        "url": url,
        "telephone": b.phone,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": b.address,
            "addressLocality": b.city.name,
        },
    }

    description = clean_text(b.about or b.description, 300)
    if description:
        data["description"] = description
    if b.city.state:
        data["address"]["addressRegion"] = b.city.state
    if b.city.country:
        data["address"]["addressCountry"] = b.city.country.code

    images = []
    if b.cover_image:
        images.append(absolute(b.cover_image.url))
    images += [absolute(p.image.url) for p in photos[:8]]
    if images:
        data["image"] = images
    if b.logo:
        data["logo"] = absolute(b.logo.url)
    if b.email:
        data["email"] = b.email
    if b.website:
        data["sameAs"] = [b.website]
    if b.latitude is not None and b.longitude is not None:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(b.latitude),
            "longitude": float(b.longitude),
        }

    specs = [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": DAY_NAMES[h.day],
            "opens": h.opens.strftime("%H:%M"),
            "closes": h.closes.strftime("%H:%M"),
        }
        for h in hours
        if not h.is_closed and h.opens and h.closes
    ]
    if specs:
        data["openingHoursSpecification"] = specs

    # Only from real, approved reviews on this site
    if reviews:
        avg = sum(r.rating for r in reviews) / len(reviews)
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": round(avg, 1),
            "reviewCount": len(reviews),
            "bestRating": 5,
            "worstRating": 1,
        }
    return data


def breadcrumb_jsonld(request, crumbs):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": name,
                "item": request.build_absolute_uri(path),
            }
            for i, (name, path) in enumerate(crumbs, start=1)
        ],
    }