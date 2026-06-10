from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("settings/profile/", views.profile_edit, name="profile_edit"),
    path("users/<str:username>/follow/", views.follow_user, name="follow_user"),
    path("users/<str:username>/unfollow/", views.unfollow_user, name="unfollow_user"),
    path("search/", views.search_users, name="search"),
]
