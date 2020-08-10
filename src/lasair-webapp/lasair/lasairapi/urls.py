from django.urls import include, path
from rest_framework import routers
from . import views

urlpatterns = [
    path('coneapi/',      views.ConeView.as_view()),
    path('streamlogapi/', views.StreamlogView.as_view()),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]

