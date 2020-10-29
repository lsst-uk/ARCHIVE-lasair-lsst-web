from django.views.generic import TemplateView
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from . import views

urlpatterns = [
    path('api',  TemplateView.as_view(template_name='api.html')),
    path('api2',  TemplateView.as_view(template_name='api2.html')),
    path('api/cone/',            views.ConeView.as_view()),
    path('api/streamlog/',       views.StreamlogView.as_view()),
    path('api/query/',           views.QueryView.as_view()),
    path('api/lightcurves/',     views.LightcurvesView.as_view()),
    path('api/sherlock/query/',  views.SherlockQueryView.as_view()),
    path('api/sherlock/object/', views.SherlockObjectView.as_view()),
    path('api/auth-token/',      obtain_auth_token, name='auth_token'),
]
