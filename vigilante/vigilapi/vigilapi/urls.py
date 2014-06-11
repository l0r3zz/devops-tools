from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'vigilapi.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^vigilante/api/v([\d\.]+)/version$', 'api.views.version'),
    url(r'^vigilante/api/v([\d\.]+)/collector/role/current/(.*)$',
        'api.views.collector_role_current'),
    url(r'^vigilante/api/v([\d\.]+)/collector/env/current/(.*)$',
        'api.views.collector_env_current'),
    url(r'^vigilante/api/v([\d\.]+)/templates/list$',
        'api.views.templates_list'),
    url(r'^vigilante/api/v([\d\.]+)/templates/get/(.*)$',
        'api.views.templates_get'),
)
