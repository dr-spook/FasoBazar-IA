from django.urls import path
from . import views

urlpatterns = [
    path('whatsapp/', views.WhatsAppWebhookView.as_view(), name='webhook-whatsapp'),
]