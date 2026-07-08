from django.urls import path
from . import views

urlpatterns = [
    path('app/',                          views.HomeView.as_view(),            name='home'),
    path('journal/',                      views.JournalView.as_view(),         name='journal'),
    path('score/',                        views.ScoreView.as_view(),           name='score'),
    path('demo/',                         views.DemoView.as_view(),            name='demo'),
    path('dashboard/',                    views.ImfDashboardView.as_view(),    name='imf-dashboard'),
    path('dashboard/<uuid:trader_id>/',   views.ImfTraderDetailView.as_view(), name='imf-detail'),
]