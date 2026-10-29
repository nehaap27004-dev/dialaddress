from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import Business, Category, City, Country


class GeoUrlTests(TestCase):
    def setUp(self):
        self.oman = Country.objects.create(name="Oman", code="OM")
        self.india = Country.objects.create(name="India", code="IN")
        self.muscat = City.objects.create(country=self.oman, name="Muscat")
        self.barka = City.objects.create(country=self.oman, name="Barka")
        self.workshops = Category.objects.create(name="Car Workshops")
        self.ac = Category.objects.create(name="AC Repair", parent=self.workshops)
        self.biz = Business.objects.create(
            name="ABC Auto Service", category=self.workshops, subcategory=self.ac,
            city=self.barka, address="Main Street", phone="96812345678",
        )

    def test_slugs(self):
        self.assertEqual(self.oman.slug, "oman")
        self.assertEqual(self.muscat.slug, "muscat")
        self.assertEqual(self.biz.slug, "abc-auto-service-barka")

    def test_pages_open_and_show_the_business(self):
        for url in ["/oman/", "/oman/barka/", "/oman/car-workshops/", "/oman/ac-repair/",
                    "/oman/barka/car-workshops/", "/oman/barka/ac-repair/"]:
            self.assertContains(self.client.get(url), "ABC Auto Service", msg_prefix=url)

    def test_business_profile_url(self):
        self.assertEqual(self.client.get("/business/abc-auto-service-barka/").status_code, 200)

    def test_empty_but_valid_pages_are_noindex(self):
        for url in ["/oman/muscat/", "/oman/muscat/car-workshops/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertContains(r, "noindex")

    def test_unknown_slugs_are_404(self):
        for url in ["/narnia/", "/oman/nowhere/", "/oman/barka/nothing/", "/oman/nowhere/car-workshops/"]:
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_wrong_country_redirects(self):
        r = self.client.get("/india/barka/")
        self.assertRedirects(r, "/oman/barka/", status_code=301, fetch_redirect_response=False)
        r = self.client.get("/india/barka/car-workshops/")
        self.assertRedirects(r, "/oman/barka/car-workshops/", status_code=301, fetch_redirect_response=False)

    def test_uppercase_redirects_to_lowercase(self):
        r = self.client.get("/Oman/Barka/")
        self.assertRedirects(r, "/oman/barka/", status_code=301, fetch_redirect_response=False)

    def test_old_urls_redirect(self):
        r = self.client.get(reverse("category_page", args=[self.workshops.slug]))
        self.assertRedirects(r, "/oman/car-workshops/", status_code=301, fetch_redirect_response=False)
        r = self.client.get(reverse("city_page", args=[self.barka.slug]))
        self.assertRedirects(r, "/oman/barka/", status_code=301, fetch_redirect_response=False)

    def test_searching_a_category_name_goes_to_the_clean_url(self):
        r = self.client.get(reverse("search"), {"q": "Car Workshops", "city": self.barka.pk})
        self.assertRedirects(r, "/oman/barka/car-workshops/", fetch_redirect_response=False)

    def test_free_text_search_still_works(self):
        self.assertContains(self.client.get(reverse("search"), {"q": "ABC"}), "ABC Auto Service")

    def test_reserved_country_name_is_refused(self):
        with self.assertRaises(ValidationError):
            Country(name="Search", code="SX").full_clean()