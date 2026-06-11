from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from tweets.models import Tweet

from .forms import LoginForm, ProfileEditForm, RegisterForm
from .models import Follow, User


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                next_url = request.POST.get("next") or request.GET.get("next") or ""
                if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)
                return redirect("home")
            form.add_error(None, "Invalid username/email or password.")
    else:
        form = LoginForm()
    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


@login_required
def home(request):
    # Placeholder until timeline is implemented (step 11).
    return HttpResponse("<h1>Home</h1><p>Timeline coming soon.</p>", content_type="text/html")


@login_required
def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    following_count = Follow.objects.filter(follower=profile_user).count()
    followers_count = Follow.objects.filter(following=profile_user).count()
    is_following = (
        request.user != profile_user
        and Follow.objects.filter(follower=request.user, following=profile_user).exists()
    )
    tweets = (
        Tweet.objects
        .filter(author=profile_user)
        .select_related("author")
        .order_by("-created_at")
    )
    return render(request, "accounts/profile.html", {
        "profile_user": profile_user,
        "following_count": following_count,
        "followers_count": followers_count,
        "is_following": is_following,
        "tweets": tweets,
    })


@login_required
def follow_user(request, username):
    if request.method != "POST":
        return redirect("profile", username=username)
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return HttpResponseBadRequest("You cannot follow yourself.")
    Follow.objects.get_or_create(follower=request.user, following=target)
    return redirect("profile", username=username)


@login_required
def unfollow_user(request, username):
    if request.method != "POST":
        return redirect("profile", username=username)
    target = get_object_or_404(User, username=username)
    Follow.objects.filter(follower=request.user, following=target).delete()
    return redirect("profile", username=username)


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile", username=request.user.username)
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def search_users(request):
    query = request.GET.get("q", "").strip()
    users = User.objects.none()
    if query:
        following_qs = Follow.objects.filter(
            follower=request.user,
            following=OuterRef("pk"),
        )
        users = (
            User.objects
            .exclude(pk=request.user.pk)
            .filter(
                Q(username__icontains=query) |
                Q(display_name__icontains=query)
            )
            .annotate(is_following=Exists(following_qs))
            .order_by("username")
        )
    return render(request, "accounts/search.html", {"users": users, "query": query})
