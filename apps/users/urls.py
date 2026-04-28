from django.urls import path

from apps.users.views import UserLoginView, UserLogoutView, register_view

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
]