from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import TweetForm
from .models import Tweet


@login_required
def timeline(request):
    tweets = Tweet.objects.select_related("author").order_by("-created_at")[:20]
    return render(request, "tweets/timeline.html", {"tweets": tweets})


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
