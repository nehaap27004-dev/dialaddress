from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from directory.models import Category
from directory.tests import make_business
from directory.models import Category, City, Review

User = get_user_model()


class DashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "b@example.com", "pass12345")
        self.staff = User.objects.create_user("staff", "s@example.com", "pass12345", is_staff=True)
        self.member = User.objects.create_user("member", "m@example.com", "pass12345")

    def test_anonymous_goes_to_login(self):
        r = self.client.get(reverse("dashboard:home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r.url)

    def test_normal_user_is_forbidden(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 403)

    def test_staff_without_permission_is_forbidden(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:business_list")).status_code, 403)

    def test_superuser_can_open_every_page(self):
        self.client.force_login(self.admin)
        for name in ["home", "business_list", "business_add", "category_list", "category_add",
                     "group_list", "group_add", "user_list"]:
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200, name)

    def test_bulk_approve(self):
        b = make_business(is_active=False)
        self.client.force_login(self.admin)
        r = self.client.post(reverse("dashboard:business_action"), {"action": "approve", "ids": [b.pk]})
        self.assertEqual(r.status_code, 302)
        b.refresh_from_db()
        self.assertTrue(b.is_active)

    def test_blocking_a_user_hides_their_listings(self):
        b = make_business(owner=self.member)
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:user_action", args=[self.member.pk]), {"action": "block"})
        self.member.refresh_from_db()
        b.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertFalse(b.is_active)

    def test_cannot_delete_a_category_that_has_businesses(self):
        b = make_business()
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:category_delete", args=[b.category_id]))
        self.assertTrue(Category.objects.filter(pk=b.category_id).exists())
    def test_new_pages_open(self):
        self.client.force_login(self.admin)
        for name in ["country_list", "country_add", "city_list", "city_add",
                     "feature_list", "feature_add", "review_list"]:
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}")).status_code, 200, name)

    def test_hiding_a_review_updates_the_rating(self):
        b = make_business()
        r = Review.objects.create(business=b, name="Asha", rating=5)
        b.refresh_from_db()
        self.assertEqual(b.review_count, 1)
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:review_action"), {"action": "hide", "ids": [r.pk]})
        b.refresh_from_db()
        self.assertEqual(b.review_count, 0)

    def test_cannot_delete_a_city_that_has_businesses(self):
        b = make_business()
        self.client.force_login(self.admin)
        self.client.post(reverse("dashboard:city_delete", args=[b.city_id]))
        self.assertTrue(City.objects.filter(pk=b.city_id).exists())