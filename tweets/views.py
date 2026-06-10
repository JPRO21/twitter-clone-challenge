from django.contrib.auth.decorators import login_required
from django.core.paginator import InvalidPage, Paginator
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TweetForm
from .models import Like, Tweet


PAGE_SIZE = 20


@login_required
def timeline(request):
    qs = (
        Tweet.objects
        .select_related("author")
        .annotate(
            like_count=Count("likes"),
            user_liked=Exists(
                Like.objects.filter(user=request.user, tweet=OuterRef("pk"))
            ),
        )
        .order_by("-created_at")
    )
    paginator = Paginator(qs, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", 1))
    except InvalidPage:
        page_obj = paginator.page(1)
    return render(request, "tweets/timeline.html", {
        "tweets": page_obj.object_list,
        "page_obj": page_obj,
    })


@login_required
def tweet_create(request):
    if request.method == "POST":
        form = TweetForm(request.POST)
        if form.is_valid():
            tweet = form.save(commit=False)
            tweet.author = request.user
            tweet.save()
            return redirect("profile", username=request.user.username)
    else:
        form = TweetForm()
    return render(request, "tweets/create.html", {"form": form})


@login_required
def like_tweet(request, pk):
    if request.method != "POST":
        return redirect("timeline")
    tweet = get_object_or_404(Tweet, pk=pk)
    Like.objects.get_or_create(user=request.user, tweet=tweet)
    return redirect("timeline")


@login_required
def unlike_tweet(request, pk):
    if request.method != "POST":
        return redirect("timeline")
    tweet = get_object_or_404(Tweet, pk=pk)
    Like.objects.filter(user=request.user, tweet=tweet).delete()
    return redirect("timeline")


@login_required
def tweet_delete(request, pk):
    if request.method != "POST":
        return redirect("timeline")
    tweet = get_object_or_404(Tweet, pk=pk)
    if tweet.author != request.user:
        return HttpResponseForbidden()
    tweet.delete()
    return redirect("timeline")
