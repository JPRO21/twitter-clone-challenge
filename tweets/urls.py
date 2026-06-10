from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.tweet_create, name="tweet_create"),
]
