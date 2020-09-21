from django.views.generic import TemplateView
from django.urls import include, path
from rest_framework import routers
from . import views

urlpatterns = [
    path('api',  TemplateView.as_view(template_name='api.html')),
    path('api/cone/',      views.ConeView.as_view()),
    path('api/streamlog/', views.StreamlogView.as_view()),
    path('api/query/',     views.QueryView.as_view()),
#    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]
