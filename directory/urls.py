from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("photos/", views.photo_gallery, name="photos"),
    path("category/<slug:slug>/", views.category_page, name="category_page"),
    path("city/<slug:slug>/", views.city_page, name="city_page"),
    path("business/<slug:slug>/", views.business_detail, name="business_detail"),
    path("business/<slug:slug>/edit/", views.edit_business, name="edit_business"),
    path("business/<slug:slug>/hours/", views.manage_hours, name="manage_hours"),
    path("business/<slug:slug>/photos/", views.manage_photos, name="manage_photos"),

    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(
        template_name="directory/login.html",
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("add-business/", views.add_business, name="add_business"),
    path("my-businesses/", views.my_businesses, name="my_businesses"),
]