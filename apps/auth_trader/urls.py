from django.urls import path
from . import views

urlpatterns = [
    path('',        views.SplashView.as_view(),   name='splash'),
    path('login/',  views.LoginView.as_view(),     name='trader-login'),
    path('logout/', views.LogoutView.as_view(),    name='trader-logout'),
    path('signup/', views.RegisterView.as_view(),  name='trader-signup'),
]