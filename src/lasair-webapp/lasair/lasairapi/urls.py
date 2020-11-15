from django.views.generic import TemplateView
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from . import views

urlpatterns = [
    path('api',  TemplateView.as_view(template_name='api.html')),
    path('api/cone/',                  views.ConeView.as_view()),
    path('api/streams/',               views.StreamsView.as_view()),
    path('api/streams/<slug:topic>/',  views.StreamsView.as_view()),
    path('api/query/',                 views.QueryView.as_view()),
    path('api/lightcurves/',           views.LightcurvesView.as_view()),
    path('api/sherlock/objects/',      views.SherlockObjectsView.as_view()),
    path('api/sherlock/position/',     views.SherlockPositionView.as_view()),
    path('api/auth-token/',            obtain_auth_token, name='auth_token'),
]
