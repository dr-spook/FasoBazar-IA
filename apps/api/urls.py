from django.urls import path
from . import views

urlpatterns = [
    path('transcribe/',                          views.TranscribeView.as_view(),     name='api-transcribe'),
    path('transactions/',                        views.TransactionsView.as_view(),   name='api-transactions'),
    path('traders/<uuid:trader_id>/score/',      views.TraderScoreView.as_view(),    name='api-score'),
    path('dashboard/',                           views.DashboardView.as_view(),      name='api-dashboard'),
    path('health/',                              views.HealthView.as_view(),         name='api-health'),
    path('fixtures/',                            views.FixturesListView.as_view(),   name='api-fixtures'),
    path('fixtures/<str:fixture_id>/play/',      views.FixturePlayView.as_view(),    name='api-fixture-play'),
]