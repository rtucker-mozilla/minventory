from django.conf.urls import url, include
from django.conf import settings
#from django.contrib import admin
from django.conf.urls.static import static
from rest_framework import routers

from middleware.restrict_to_remote import allow_anyone

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
#admin.autodiscover()
import systems.views as system_views
import invapi.views as apiviews

system_detail = apiviews.SystemViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
})

system_root = apiviews.SystemViewSet.as_view({
        'get': 'list',
        'post': 'create',
})

router = routers.DefaultRouter()
router.register(r'systemstatus', apiviews.SystemStatusViewSet)
router.register(r'servermodel', apiviews.ServerModelViewSet)
router.register(r'operatingsystem', apiviews.OperatingSystemViewSet)
router.register(r'systemtype', apiviews.SystemTypeViewSet)
router.register(r'systemrack', apiviews.SystemRackViewSet)


urlpatterns = [
    # Example:


    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
#    url(r'^admin/', include(admin.site.urls)),
#    url(r'^api/', include(router.urls)),
    url(r'^tokenapi/systems/$', system_root, name="tokenapi-system-root"),
    url(r'^tokenapi/systems/(?P<pk>.+)/$', system_detail, name="tokenapi-system-detail"),
    url(r'^tokenapi/', include(router.urls)),
    url(r'^$', system_views.home, name='system-home'),
    url(r'^en-US/$', system_views.home, name='system-home'),
    url(r'^a(\d+)/$', system_views.system_show_by_asset_tag),
    url(r'^systems/', include('systems.urls')),
    url(r'^csv/', include('mcsv.urls')),
    url(r'^en-US/systems/', include('systems.urls')),
#    (r'^oncall/', include('oncall.urls')),
#    (r'^bulk_action/', include('bulk_action.urls')),
#    (r'^decommission/', include('decommission.urls')),
#    (r'^reports/', include('reports.urls')),
#    (r'^truth/', include('truth.urls')),

]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
