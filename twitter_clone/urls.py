from django.contrib import admin
from django.urls import include, path

from tweets import views as tweet_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Timeline serves as the authenticated homepage; "home" kept for
    # existing reverse("home") calls, "timeline" added for spec tests.
    path("", tweet_views.timeline, name="home"),
    path("timeline/", tweet_views.timeline, name="timeline"),
    path("", include("accounts.urls")),
    path("tweets/", include("tweets.urls")),
]
