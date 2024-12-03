# multymessenger/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home route
    path('file-upload/', views.file_upload_endpoint, name='file_upload_endpoint'),  # Add this line
]
