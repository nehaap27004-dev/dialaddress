from django.urls import path

from . import views as v

app_name = "dashboard"

urlpatterns = [
    path("", v.HomeView.as_view(), name="home"),

    path("businesses/", v.BusinessListView.as_view(), name="business_list"),
    path("businesses/add/", v.BusinessAddView.as_view(), name="business_add"),
    path("businesses/action/", v.BusinessActionView.as_view(), name="business_action"),
    path("businesses/<int:pk>/edit/", v.BusinessEditView.as_view(), name="business_edit"),
    path("businesses/<int:pk>/delete/", v.BusinessDeleteView.as_view(), name="business_delete"),
    path("api/subcategories/", v.SubcategoryOptionsView.as_view(), name="subcategories"),

    path("categories/", v.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", v.CategoryAddView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", v.CategoryEditView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", v.CategoryDeleteView.as_view(), name="category_delete"),

    path("groups/", v.GroupListView.as_view(), name="group_list"),
    path("groups/add/", v.GroupAddView.as_view(), name="group_add"),
    path("groups/<int:pk>/edit/", v.GroupEditView.as_view(), name="group_edit"),
    path("groups/<int:pk>/delete/", v.GroupDeleteView.as_view(), name="group_delete"),

    path("users/", v.UserListView.as_view(), name="user_list"),
    path("users/<int:pk>/edit/", v.UserEditView.as_view(), name="user_edit"),
    path("users/<int:pk>/action/", v.UserActionView.as_view(), name="user_action"),
        path("countries/", v.CountryListView.as_view(), name="country_list"),
    path("countries/add/", v.CountryAddView.as_view(), name="country_add"),
    path("countries/<int:pk>/edit/", v.CountryEditView.as_view(), name="country_edit"),
    path("countries/<int:pk>/delete/", v.CountryDeleteView.as_view(), name="country_delete"),

    path("cities/", v.CityListView.as_view(), name="city_list"),
    path("cities/add/", v.CityAddView.as_view(), name="city_add"),
    path("cities/<int:pk>/edit/", v.CityEditView.as_view(), name="city_edit"),
    path("cities/<int:pk>/delete/", v.CityDeleteView.as_view(), name="city_delete"),

    path("features/", v.FeatureListView.as_view(), name="feature_list"),
    path("features/add/", v.FeatureAddView.as_view(), name="feature_add"),
    path("features/<int:pk>/edit/", v.FeatureEditView.as_view(), name="feature_edit"),
    path("features/<int:pk>/delete/", v.FeatureDeleteView.as_view(), name="feature_delete"),

    path("reviews/", v.ReviewListView.as_view(), name="review_list"),
    path("reviews/action/", v.ReviewActionView.as_view(), name="review_action"),
    path("reviews/<int:pk>/edit/", v.ReviewEditView.as_view(), name="review_edit"),
    path("reviews/<int:pk>/delete/", v.ReviewDeleteView.as_view(), name="review_delete"),
]