from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from apps.accounts.services import provision_account_for_user
from apps.users.forms import EmailAuthenticationForm, RegistrationForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect("event-list")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            provision_account_for_user(user, form.cleaned_data["account_name"])
            login(request, user)
            messages.success(request, "Welcome. Your Free Tier account is ready.")
            return redirect("event-list")
    else:
        form = RegistrationForm()

    return render(request, "users/register.html", {"form": form})


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = EmailAuthenticationForm


class UserLogoutView(LogoutView):
    pass