from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", account_views.home, name="home"),
    path("", include("accounts.urls")),
    path("tweets/", include("tweets.urls")),
]
