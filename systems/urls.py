from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^quicksearch/$', views.system_quicksearch_ajax),
    url(r'^list_all_systems_ajax/$', views.list_all_systems_ajax),
    url(r'^get_network_adapters/(\d+)[/]$', views.get_network_adapters),
    url(r'^create_network_adapter/(\d+)[/]$', views.create_network_adapter),
    url(r'^get_expanded_key_value_store/(\d+)[/]$', views.get_expanded_key_value_store),
    url(r'^delete_network_adapter/(\d+)/(\d+)[/]$', views.delete_network_adapter),
    url(r'^save_network_adapter/(\d+)[/]$', views.save_network_adapter),
    url(r'^get_key_value_store/(\d+)[/]$', views.get_key_value_store),
    url(r'^create_key_value/(?P<a_id>\d+)[/]$', views.create_key_value),
    url(r'^delete_key_value/(?P<a_id>\d+)/(?P<system_id>\d+)[/]$', views.delete_key_value),
    url(r'^save_key_value/(\d+)[/]$', views.save_key_value),
    url(r'^new/$', views.system_new, name='system-new'),
    url(r'^show/(?P<a_id>\d+)[/]$', views.system_show),
    url(r'^show/a(?P<a_id>\d+)[/]$', views.system_show_by_asset_tag),
    url(r'^edit/(?P<a_id>\d+)[/]$', views.system_edit, name="system-edit"),
    url(r'^revision/(?P<pk>\d+)[/]$', views.SystemRevision.as_view()),
    url(
        r'^operatingsystems[/]$',
        views.OperatingSystemListView.as_view(),
        name="operatingsystem-list"
    ),
    url(
        r'^operatingsystem/delete/(?P<pk>\d+)[/]$',
        views.OperatingSystemDeleteView.as_view(),
        name="operatingsystem-delete"
    ),
    url(
        r'^operatingsystem/create[/]$',
        views.OperatingSystemCreateView.as_view(),
        name="operatingsystem-new"
    ),
    url(
        r'^operatingsystem/edit/(?P<pk>\d+)[/]$',
        views.OperatingSystemEditView.as_view(),
        name="operatingsystem-edit"
    ),
    url(r'^delete/(\d+)[/]$', views.system_delete),
    url(
        r'^ajax_check_dupe_nic/(?P<system_id>\d+)/(?P<adapter_number>\d+)[/]$',
        views.check_dupe_nic
    ),
    url(r'^system_auto_complete_ajax[/]$', views.system_auto_complete_ajax),
    url(
        r'^ajax_check_dupe_nic_name/(?P<system_id>\d+)/(?P<adapter_name>.*)[/]$',
        views.check_dupe_nic_name
    ),
    url(r'^sync_external_data/$', views.sync_external_data_ajax),
    url(r'^csv/$', views.system_csv, name="system-csv"),
    url(r'^csv/import/$', views.csv_import, name='system-csv-import'),
    url(r'^racks/$', views.racks, name='system_rack-list'),
    url(r'^racks/delete/(?P<object_id>\d+)/$', views.rack_delete, name='rack-delete'),
    url(r'^racks/new/$', views.rack_new, name="system_rack-new"),
    url(
        r'^racks/edit/(?P<object_id>\d+)/$',
        views.rack_edit,
        name="system_rack-edit"
    ),
    url(
        r'^racks/system/new/(?P<rack_id>\d+)/$',
        views.new_rack_system_ajax,
        name='racks-system-new'
    ),
    url(
        r'^racks/bysite/(?P<site_pk>\d+)/$',
        views.racks_by_site,
        name='system-racks-by-site'
    ),
    url(
        r'^racks/ajax_racks_by_site/(?P<site_pk>\d+)/$',
        views.ajax_racks_by_site,
        name='racks-by-site'
    ),
    url(
        r'^server_models/new/$',
        views.server_model_create,
        name="server_model-new"
    ),
    url(
        r'^server_models/edit/(?P<object_id>\d+)/$',
        views.server_model_edit,
        name="server_model-edit"
    ),
    url(r'^server_models/$', views.server_model_list, name="server_model-list"),
    url(
        r'^server_models/create_ajax/$',
        views.server_model_create_ajax,
        name="server_model_create_ajax"
    ),
    url(r'^server_models/list_ajax/$', views.server_model_list_ajax, name="server_model_list_ajax"),
    url(
        r'^operating_system/create_ajax/$',
        views.operating_system_create_ajax,
        name="server_model_create_ajax"
    ),
    url(
        r'^operating_system/list_ajax/$',
        views.operating_system_list_ajax,
        name="server_model_list_ajax"
    ),
    url(
        r'^server_models/show/(?P<object_id>\d+)/$',
        views.server_model_show,
        name="server_model-show"
    ),
    #url(
    # r'^server_models/delete/(?P<object_id>\d+)/$',
    # delete_object,
    # gen_del_dict(ServerModel, 'server_model-list),
    # name='server_model-delete
    # ),
]
