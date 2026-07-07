from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.chat_message, name='chatbot_message'),
    path('reset/', views.chat_reset, name='chatbot_reset'),
    path('history/', views.chat_history, name='chatbot_history'),
]
