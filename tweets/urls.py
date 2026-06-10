from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.tweet_create, name="tweet_create"),
    path("<int:pk>/like/", views.like_tweet, name="like_tweet"),
    path("<int:pk>/unlike/", views.unlike_tweet, name="unlike_tweet"),
]
