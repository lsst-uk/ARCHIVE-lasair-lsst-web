"""lasair URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as authviews
from django.urls import include, path
from django.views.generic import TemplateView

from lasair import views, services, candidates, objects, areas, watchlists, queries, skymap
import lasair.settings

from django.contrib import admin
#admin.autodiscover()

urlpatterns = [
    path('about',                   views.about,                name='about'),
    path('sherlock',    TemplateView.as_view(template_name='sherlock.html')),
    path('lasairlsst',  TemplateView.as_view(template_name='lasairlsst.html')),
    path('release',  TemplateView.as_view(template_name='release.html')),
    path('contact',  TemplateView.as_view(template_name='contact.html')),
    # above will disappear

    path('',              views.index,                  name='index'),
    path('explore',       TemplateView.as_view(template_name='explore.html')),
    path('learn',         TemplateView.as_view(template_name='learn.html')),
    path('code',          TemplateView.as_view(template_name='code.html')),
    path('documentation', TemplateView.as_view(template_name='documentation.html')),
    path('support',       TemplateView.as_view(template_name='support.html')),

    path('conesearch/',             views.conesearch,           name='conesearch'),
    path('status/',                 views.status_today,         name='status_today'),
    path('status/<int:nid>/',       views.status,               name='status'),
    path('streams/<slug:topic>/',   views.streams,              name='streams'),
    path('fitsview/<slug:filename>/', views.fitsview,           name='fitsview'),

    path('cookbook'  , TemplateView.as_view(template_name='cookbook.html'),            name='cookbook'),
    path('cookbook/<slug:topic>/'  , views.cookbook,            name='cookbook'),
    path('faq',  TemplateView.as_view(template_name='faq.html')),

    path('cand/<int:candid>/',      candidates.cand,            name='cand'),

    path('object/<slug:objectId>/',      objects.objhtml,       name='objhtml'),
#    path('object/<slug:objectId>/json/', objects.objjson,       name='objjson'),

    path('areas/',                  areas.areas_home,           name='areas_home'),
    path('area_new/',               areas.area_new,             name='area_new'),
    path('area/<int:ar_id>/',       areas.show_area,            name='show_area'),
    path('area/<int:ar_id>/file/',  areas.show_area_file,       name='show_area_file'),

    path('watchlists/',             watchlists.watchlists_home, name='watchlists_home'),
    path('watchlist_new/',          watchlists.watchlist_new,   name='watchlist_new'),
    path('watchlist/<int:wl_id>/',  watchlists.show_watchlist,  name='show_watchlist'),
    path('watchlist/<int:wl_id>/txt/',  watchlists.show_watchlist_txt,  name='show_watchlist_txt'),

    path('querylist_all/',          queries.querylist_all,      name='querylist_all'),
    path('querylist/<slug:which>/', queries.querylist,          name='querylist'),
    path('query/',                  queries.new_myquery,          name='new_myquery'),
    path('query/<int:mq_id>/',      queries.show_myquery,         name='show_myquery'),

    path('runquery/',               queries.runquery,             name='runquery'),

    path('skymap/',                 skymap.skymap,              name='skymap'),
    path('skymap/<skymap_id_version>/',     skymap.show_skymap, name='show_skymap'),

    path('schema',   TemplateView.as_view(template_name='schema.html')),
    path('jupyter',  TemplateView.as_view(template_name='jupyter.html')),
    path('jupyter2',  TemplateView.as_view(template_name='jupyter2.html')),
    path('fits/<slug:candid_cutoutType>/',  services.fits,     name='fits'),

    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/',                  views.signup,              name='signup'),
    path('admin/',                   admin.site.urls),
    path('', include('lasairapi.urls')),
]
