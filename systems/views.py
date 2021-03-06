import csv
import re
import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import  redirect, get_object_or_404, render, render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.test.client import RequestFactory
from django.views.generic.list import ListView
from reversion.models import Version
from reversion_compare.mixins import CompareMixin
from middleware.restrict_to_remote import allow_anyone
from systems import models
from systems.models import System, SystemStatus
from systems.forms import SystemForm

# Use this object to generate request objects for calling tastypie views
factory = RequestFactory()

# Source: http://nedbatchelder.com/blog/200712/human_sorting.html
# Author: Ned Batchelder
def tryint(s):
    try:
        return int(s)
    except: # pylint: disable=bare-except
        return s

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [tryint(c) for c in re.split('([0-9]+)', s)]

def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)

def parse_title_num(title):
    val = 0
    try:
        val = int(title.rsplit('#')[-1])
    except ValueError:
        pass
    return val

def check_dupe_nic(request, system_id, adapter_number): # pylint: disable=unused-argument
    try:
        system = models.System.objects.get(id=system_id)
        found = system.check_for_adapter(adapter_number)
    except: # pylint: disable=bare-except
        pass
    return HttpResponse(found)

def check_dupe_nic_name(request, system_id, adapter_name): # pylint: disable=unused-argument
    try:
        system = models.System.objects.get(id=system_id)
        found = system.check_for_adapter_name(adapter_name)
    except: # pylint: disable=bare-except
        pass
    return HttpResponse(found)


@allow_anyone
def system_auto_complete_ajax(request):
    query = request.GET['query']
    system_list = models.System.objects.filter(hostname__icontains=query)
    hostname_list = [system.hostname for system in system_list]
    id_list = [system.id for system in system_list]
    ret_dict = {}
    ret_dict['query'] = query
    ret_dict['suggestions'] = hostname_list
    ret_dict['data'] = id_list
    return HttpResponse(json.dumps(ret_dict))

@allow_anyone
def list_all_systems_ajax(request):
#iSortCol_0 = which column is sorted
#sSortDir_0 = which direction

    cols = [
        'hostname',
        'serial',
        'asset_tag',
        'server_model',
        'system_rack',
        'oob_ip',
        'system_status'
    ]
    sort_col = cols[0]
    if 'iSortCol_0' in request.GET:
        sort_col = cols[int(request.GET['iSortCol_0'])]

    sort_dir = 'asc'
    if 'sSortDir_0' in request.GET:
        sort_dir = request.GET['sSortDir_0']


    if 'sEcho' in request.GET:
        sEcho = request.GET['sEcho']

    if 'sSearch' in request.GET and request.GET['sSearch'] > '':
        search_term = request.GET['sSearch']
    else:
        search_term = None

    if 'iDisplayLength' in request.GET and request.GET['iDisplayLength'] > '':
        iDisplayLength = request.GET['iDisplayLength']
    else:
        iDisplayLength = 100

    if 'iDisplayStart' in request.GET\
        and request.GET['iDisplayStart'] > '':
        iDisplayStart = request.GET['iDisplayStart']
    else:
        iDisplayStart = 0

    if search_term is None:
        end_display = int(iDisplayStart) + int(iDisplayLength)
        system_count = models.System.objects.all().count()
        systems = models.System.objects.all()[int(iDisplayStart):int(end_display)]
        the_data = build_json(
            request,
            systems,
            sEcho,
            system_count,
            iDisplayLength,
            sort_col,
            sort_dir
        )

    if search_term is not None and len(search_term) > 0: # pylint: disable=len-as-condition
        if search_term.startswith('/') and len(search_term) > 1:
            try:
                search_term = search_term[1:]
                search_q = Q(hostname__regex=search_term)
            except: # pylint: disable=bare-except
                search_q = Q(hostname__icontains=search_term)
        else:
            search_q = Q(hostname__icontains=search_term)
        search_q |= Q(serial__icontains=search_term)
        search_q |= Q(notes__icontains=search_term)
        search_q |= Q(asset_tag=search_term)
        search_q |= Q(oob_ip__icontains=search_term)
        search_q |= Q(keyvalue__value__icontains=search_term)
        try:
            total_count = models.System.with_related\
                .filter(search_q).values('hostname').distinct().count()
        except: # pylint: disable=bare-except
            total_count = 0
        end_display = int(iDisplayStart) + int(iDisplayLength)
        try:
            systems = models.System.objects.filter(
                pk__in=models.System.with_related\
                    .filter(search_q).values_list('id', flat=True).distinct()
            )[int(iDisplayStart):int(end_display)]
            the_data = build_json(
                request,
                systems,
                sEcho,
                total_count,
                iDisplayLength,
                sort_col,
                sort_dir
            )
        except: # pylint: disable=bare-except
            the_data = '{"sEcho": %s, "iTotalRecords":0, "iTotalDisplayRecords":0, "aaData":[]}' % (sEcho) # pylint: disable=line-too-long
    return HttpResponse(the_data)

def build_json(request, systems, sEcho, total_records, display_count, sort_col, sort_dir):
    system_list = []
    for system in systems:
        if system.serial is not None:
            serial = system.serial.strip()
        else:
            serial = ''

        if system.server_model is not None:
            server_model = str(system.server_model)
        else:
            server_model = ''
        if system.system_rack is not None:
            system_rack = "%s - %s" % (str(system.system_rack), system.rack_order)
            system_rack_id = str(system.system_rack.id)
        else:
            system_rack = ''
            system_rack_id = ''

        if system.system_status is not None:
            system_status = str(system.system_status)
        else:
            system_status = ''

        if system.asset_tag is not None:
            asset_tag = system.asset_tag.strip()
        else:
            asset_tag = ''
        if system.oob_ip is not None:
            oob_ip = system.oob_ip.strip()
        else:
            oob_ip = ''

        ro = getattr(request, 'read_only', False)
        if ro:
            system_id = 0
        else:
            system_id = system.id

        system_list.append(
            {
                'hostname': system.hostname.strip(),
                'oob_ip': oob_ip,
                'serial': serial,
                'asset_tag': asset_tag,
                'server_model': server_model,
                'system_rack':system_rack,
                'system_status':system_status,
                'id':system_id,
                'system_rack_id': system_rack_id
            }
        )

    the_data = '{"sEcho": %s, "iTotalRecords":0, "iTotalDisplayRecords":0, "aaData":[]}' % (sEcho)

    #try:
    if system_list:
        system_list.sort(key=lambda x: alphanum_key(x[sort_col]))
        if sort_dir == 'desc':
            system_list.reverse()
        the_data = '{"sEcho": %s, "iTotalRecords":%i, "iTotalDisplayRecords":%i, "aaData":[' % (
            sEcho,
            total_records,
            total_records
        )
        counter = 0
        for system in system_list:
            if int(counter) < int(display_count):
                the_data += '["%i,%s","%s","%s","%s","%s,%s", "%s", "%s", "%i"],' % (
                    system['id'],
                    system['hostname'],
                    system['serial'],
                    system['asset_tag'],
                    system['server_model'],
                    system['system_rack_id'],
                    system['system_rack'],
                    system['oob_ip'],
                    system['system_status'],
                    system['id']
                )
                counter += 1
            else:
                counter = display_count
        the_data = the_data[:-1]
        the_data += ']}'

    return the_data


#@ldap_group_required('build')
#@LdapGroupRequired('build_team', exclusive=False)
@allow_anyone
def home(request): # pylint: disable=unused-argument
    """Index page"""
    return render_to_response('systems/index.html', {
        'read_only': False,
    })

@allow_anyone
def system_quicksearch_ajax(request):
    """Returns systems sort table"""
    search_term = request.POST['quicksearch']
    search_q = Q(hostname__icontains=search_term)
    search_q |= Q(serial__contains=search_term)
    search_q |= Q(notes__contains=search_term)
    search_q |= Q(asset_tag=search_term)
    systems = models.System.with_related.filter(search_q).order_by('hostname')
    if 'is_test' not in request.POST:
        return render_to_response('systems/quicksearch.html', {
            'systems': systems,
            'read_only': getattr(request, 'read_only', False),
        }, RequestContext(request))
    else:
        from django.core import serializers
        systems_data = serializers.serialize("json", systems)
        return HttpResponse(systems_data)


def get_key_value_store(request, a_id):
    system = models.System.objects.get(id=a_id)
    key_value_store = models.KeyValue.objects.filter(obj=system)
    return render_to_response('systems/key_value_store.html', {
        'key_value_store': key_value_store,
    }, RequestContext(request))


def delete_key_value(request, a_id, system_id):
    kv = models.KeyValue.objects.get(id=a_id)
    matches = re.search(r'^nic\.(\d+)', str(kv.key))
    if matches:
        try:
            existing_dhcp_scope = models.KeyValue.objects.filter(obj=kv.system)\
                .filter(key='nic.%s.dhcp_scope.0' % matches.group(1))[0].value
            models.ScheduledTask(task=existing_dhcp_scope, type='dhcp').save()
        except: # pylint: disable=bare-except
            pass
    kv.delete()
    system = models.System.objects.get(id=system_id)
    key_value_store = models.KeyValue.objects.filter(obj=system)
    return render_to_response('systems/key_value_store.html', {
        'key_value_store': key_value_store,
    }, RequestContext(request))


@csrf_exempt
def save_key_value(request, a_id):
    validated = True
    resp = {'success': True, 'errorMessage' : ''}
    post_key = request.POST.get('key').strip()
    post_value = request.POST.get('value').strip()
    try:
        tmp = models.KeyValue.objects.get(id=a_id)
        system = tmp.system
    except Exception as exc: # pylint: disable=broad-except
        print(exc)


    # This is probably actually an issue but this code never gets called
    acl = KeyValueACL(request) # pylint: disable=bad-option-value,undefined-variable
    if post_key == 'shouldfailvalidation':
        resp['success'] = False
        resp['errorMessage'] = 'Validation Failed'
        validated = False
    kv = models.KeyValue.objects.get(id=id)
    if kv is not None and validated:
        # Here we eant to check if the existing key is a network adapter.
        # If so we want to find out if it has a dhcp scope.
        # If so then we want to add it to ScheduledTasks so that the dhcp file gets regenerated
        matches = re.search(r'^nic\.(\d+)', str(kv.key).strip())
        """
            Check to see if we have a network adapter
            If so we need to flag the dhcp zone file to be regenerated
        """
        if matches and matches.group(1):
            """
                Check to see if it's an ipv4_address key
                run KeyValueACL.check_ip_not_exist_other_system
            """
            if re.search(r'^nic\.(\d+)\.ipv4_address', str(post_key).strip()):
                try:
                    acl.check_ip_not_exist_other_system(system, post_value)
                except Exception as exc: # pylint: disable=broad-except
                    resp['success'] = False
                    resp['errorMessage'] = str(exc)
                    return HttpResponse(json.dumps(resp))
            try:
                existing_dhcp_scope = models.KeyValue.objects.filter(obj=kv.system)\
                    .filter(key='nic.%s.dhcp_scope.0' % matches.group(1))[0].value
                if existing_dhcp_scope is not None:
                    models.ScheduledTask(task=existing_dhcp_scope, type='dhcp').save()
            except Exception: # pylint: disable=broad-except
                pass
            try:
                existing_reverse_dns_zone = models.KeyValue.objects\
                    .filter(obj=kv.system)\
                    .filter(key='nic.%s.reverse_dns_zone.0' % matches.group(1))[0].value
                if existing_reverse_dns_zone is not None:
                    models.ScheduledTask(
                        task=existing_reverse_dns_zone,
                        type='reverse_dns_zone'
                    ).save()
            except Exception: # pylint: disable=broad-except
                pass
        try:
            kv.key = request.POST.get('key').strip()
            kv.value = request.POST.get('value').strip()
            kv.save()
        except: # pylint: disable=bare-except
            kv.key = None
            kv.value = None
        # Here we eant to check if the new key is a network adapter.
        # If so we want to find out if it has a dhcp scope.
        # If so then we want to add it to ScheduledTasks so that the dhcp file gets regenerated
        if kv.key is not None:
            matches = re.search(r'nic\.(\d+)', kv.key)
            if matches and matches.group(1):
                new_dhcp_scope = None
                new_reverse_dns_zone = None
                try:
                    new_dhcp_scope = models.KeyValue.objects\
                        .filter(obj=kv.system)\
                        .filter(key='nic.%s.dhcp_scope.0' % matches.group(1))[0].value
                except: # pylint: disable=bare-except
                    pass

                try:
                    new_reverse_dns_zone = models.KeyValue.objects\
                        .filter(obj=kv.system)\
                        .filter(key='nic.%s.reverse_dns_zone.0' % matches.group(1))[0].value
                except: # pylint: disable=bare-except
                    pass
                if new_dhcp_scope is not None:
                    try:
                        models.ScheduledTask(task=new_dhcp_scope, type='dhcp').save()
                    except Exception as exc: # pylint: disable=broad-except
                        print(exc)
                if new_reverse_dns_zone is not None:
                    try:
                        models.ScheduledTask(
                            task=new_reverse_dns_zone,
                            type='reverse_dns_zone'
                        ).save()
                    except: # pylint: disable=bare-except
                        pass


    return HttpResponse(json.dumps(resp))
    #return HttpResponseRedirect('/en-US/systems/get_key_value_store/' + system_id + '/')

@csrf_exempt
def create_key_value(request, a_id):
    system = models.System.objects.get(id=a_id)
    key = 'None'
    value = 'None'
    if 'key' in request.POST:
        key = request.POST['key'].strip()
    if 'value' in request.POST:
        value = request.POST['value'].strip()
    kv = models.KeyValue(obj=system, key=key, value=value)
    print("Key is %s: Value is %s." % (key, value))
    kv.save()
    matches = re.search(r'^nic\.(\d+)', str(kv.key))
    if matches:
        try:
            existing_dhcp_scope = models.KeyValue.objects\
                .filter(obj=kv.system)\
                .filter(key='nic.%s.dhcp_scope.0' % matches.group(1))[0].value
            models.ScheduledTask(task=existing_dhcp_scope, type='dhcp').save()
        except: # pylint: disable=bare-except
            pass
    key_value_store = models.KeyValue.objects.filter(obj=system)
    return render_to_response('systems/key_value_store.html', {
        'key_value_store': key_value_store,
    }, RequestContext(request))

def get_network_adapters(request, a_id):
    adapters = models.NetworkAdapter.objects.filter(system_id=a_id)
    return render_to_response('systems/network_adapters.html', {
        'adapters': adapters,
        'switches': models.System.objects.filter(is_switch=1),
        'dhcp_scopes': models.DHCP.objects.all()
    }, RequestContext(request))


def delete_network_adapter(request, a_id, system_id):
    adapter = models.NetworkAdapter.objects.get(id=a_id)
    adapter.delete()
    adapters = models.NetworkAdapter.objects.filter(system_id=system_id)
    return render_to_response('systems/network_adapters.html', {
        'adapters': adapters,
        'dhcp_scopes': models.DHCP.objects.all(),
        'switches': models.System.objects.filter(is_switch=1)
    }, RequestContext(request))


def create_network_adapter(request, a_id):
    nic = models.NetworkAdapter(system_id=a_id)
    nic.save()
    adapters = models.NetworkAdapter.objects.filter(system_id=a_id)
    return render_to_response('systems/network_adapters.html', {
        'adapters': adapters,
        'dhcp_scopes': models.DHCP.objects.all(),
        'switches': models.System.objects.filter(is_switch=1)
    }, RequestContext(request))

def save_network_adapter(request, a_id):
    nic = models.NetworkAdapter.objects.get(id=a_id)
    if nic is not None:
        mac = request.POST['mac_address']
        mac = mac.replace(':', '').replace(' ', '').replace('.', '')
        tmp = mac[0:2]+ ':'\
            + mac[2:4] + ':'\
            + mac[4:6] + ':'\
            + mac[6:8] + ':'\
            + mac[8:10] + ':'\
            + mac[10:12]
        mac = tmp
        nic.dhcp_scope_id = request.POST['dhcp_scope_id']
        nic.mac_address = mac
        nic.ip_address = request.POST['ip_address']
        nic.filename = request.POST['filename']
        nic.option_host_name = request.POST['option_host_name']
        nic.option_domain_name = request.POST['option_domain_name']
        nic.adapter_name = request.POST['adapter_name']
        if request.POST['switch_id']:
            nic.switch_id = request.POST['switch_id']
        else:
            nic.switch_id = None
        nic.switch_port = request.POST['switch_port']
        nic.save()
    return HttpResponseRedirect('/systems/get_network_adapters/' + id)


def sync_external_data_ajax(request):
    attr, source, system_pk = (
        request.POST.get('attr', None),
        request.POST.get('source', None),
        request.POST.get('system_pk', None)
    )

    if not (attr and source and system_pk):
        return HttpResponse(json.dumps({
            'error': "attr, source, and system_pk are required"
        }), status=400)

    system = get_object_or_404(models.System, pk=system_pk)

    if not hasattr(system, attr):
        return HttpResponse(json.dumps({
            'error': "System has no attribute {0}".format(attr)
        }), status=400)

    try:
        ed = system.externaldata_set.get(source=source, name=attr)
    except system.externaldata_set.model.DoesNotExist:
        return HttpResponse(
            json.dumps(
                {
                    'error': "System {0} has no external attribute '{1}' for source '{2}'".format(
                        system.hostname, attr, source
                    )
                }
            ), status=400)

    conflict_seen = system.external_data_conflict(attr)
    cur_value = getattr(system, attr)
    if attr == 'oob_ip' and cur_value.strip().startswith('ssh'):
        new_value = 'ssh ' + ed.data
    else:
        new_value = ed.data

    setattr(system, attr, new_value)
    system.save(request=request)

    return HttpResponse(json.dumps({
        'conflict-seen': conflict_seen,
        'new-value': new_value
    }))


@allow_anyone
def system_show(request, a_id):
    system = get_object_or_404(models.System, pk=a_id)
    if system.notes:
        system.notes = system.notes.replace("\n", "<br />")
    show_nics_in_key_value = False
    is_release = False
    if (system.serial and
            system.server_model and
            system.server_model.part_number and
            system.server_model.vendor == "HP"):

        system.warranty_link = "http://www11.itrc.hp.com/service/ewarranty/warrantyResults.do?productNumber=%s&serialNumber1=%s&country=US" % (system.server_model.part_number, system.serial)  # noqa pylint: disable=line-too-long
    if show_nics_in_key_value:
        key_values = system.keyvalue_set.all()
    else:
        key_values = system.keyvalue_set.exclude(key__istartswith='nic.')

    sregs = []
    groups = []

    object_search_str = "(/^{0}$".format(system)
    for sreg in filter(lambda sreg: not sreg.decommissioned, sregs):
        object_search_str += " OR /^{0}$".format(sreg.fqdn)
        object_search_str += " OR /^{0}$".format(sreg.ip_str)
    object_search_str += " ) AND !type=:sreg AND !type=:sys"

    return render(request, 'systems/system_show.html', {
        'system': system,
        'object_search_str': object_search_str,
        'sregs': sregs,
        'groups': groups,
        'key_values': key_values,
        'is_release': is_release,
        'read_only': getattr(request, 'read_only', False),
    })


@allow_anyone
def system_show_by_asset_tag(request, a_id):
    system = get_object_or_404(models.System, asset_tag=a_id)
    if (system.serial and
            system.server_model and
            system.server_model.part_number and
            system.server_model.vendor == "HP"):

        system.warranty_link = "http://www11.itrc.hp.com/service/ewarranty/warrantyResults.do?productNumber=%s&serialNumber1=%s&country=US" % (system.server_model.part_number, system.serial) # pylint: disable=line-too-long

    return render_to_response('systems/system_show.html', {
        'system': system,
        'is_release': True,
        'read_only': getattr(request, 'read_only', False),
    }, RequestContext(request))


def system_view(request, template, data, instance=None):
    if request.method == 'POST':
        form = SystemForm(request.POST, instance=instance)
        if form.is_valid():
            s = form.save(commit=False)
            s.save(request=request)
            return redirect(system_show, s.pk)
    else:
        form = SystemForm(instance=instance)

    data['form'] = form

    return render_to_response(
        template,
        data,
        RequestContext(request)
    )


@csrf_exempt
def system_new(request):
    return system_view(request, 'systems/system_new.html', {})

@csrf_exempt
def system_edit(request, a_id):
    system = get_object_or_404(models.System, pk=a_id)
    versions = Version.objects.get_for_object(system)

    return system_view(request, 'systems/system_edit.html', {
        'system': system,
        'revision_history':versions
    }, system)


def system_delete(request, a_id):
    system = get_object_or_404(models.System, pk=a_id)
    try:
        kv_length = len(system.keyvalue_set.all())
    except AttributeError:
        kv_length = 0

    if kv_length == 0:
        try:
            system.delete()
        except IntegrityError as exc:
            content = "Unable to Delete system: {message}".format(message=exc)
            return render_to_response(
                'systems/generic_output.html',
                {
                    'system': system,
                    'content': content,
                },
                RequestContext(request))
    elif kv_length > 0:
        link = '/core/keyvalue/keyvalue/{id}'.format(id=system.id)
        content = """Unable to Delete system. <br />
        Please <a href="{link}">Delete Key/Value Entries</a>
        """.format(link=link)
        return render_to_response(
            'systems/generic_output.html',
            {
                'system': system,
                'content': content,
            },
            RequestContext(request))
    return redirect(home)


def system_csv(request): # pylint: disable=unused-argument
    systems = models.System.objects.all().order_by('hostname')

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=systems.csv'

    writer = csv.writer(response)
    writer.writerow(
        [
            'Host Name',
            'Serial',
            'Asset Tag',
            'Model',
            'Allocation',
            'Rack',
            'Switch Ports',
            'OOB IP'
        ]
    )
    for s in systems:
        try:
            writer.writerow(
                [
                    s.hostname,
                    s.serial,
                    s.asset_tag,
                    s.server_model,
                    s.system_rack,
                    s.switch_ports,
                    s.oob_ip
                ]
            )
        except: # pylint: disable=bare-except
            writer.writerow(
                [
                    s.hostname,
                    s.serial,
                    s.asset_tag,
                    s.server_model,
                    '',
                    s.system_rack,
                    s.switch_ports,
                    s.oob_ip
                ]
            )


    return response

def get_expanded_key_value_store(request, system_id):
    try:
        system = models.System.objects.get(id=system_id)
        request = factory.get(
            '/api/v2/keyvalue/3/',
            {
                'key_type':'adapters_by_system',
                'system':system.hostname
            }
        )
        h = KeyValueHandler()
        request = factory.get('/api/keyvalue/?keystore=%s' % (system.hostname), follow=True)
        resp = json.dumps(h.read(request, key_value_id='3'))
        return_obj = resp.replace(",", ",<br />")
    except: # pylint: disable=bare-except
        return_obj = 'This failed'
    return HttpResponse(return_obj)


def new_rack_system_ajax(request, rack_id):
    from .forms import RackSystemForm
    rack = get_object_or_404(models.SystemRack, pk=rack_id)

    data = {}
    resp_data = {}
    template = 'systems/rack_form_partial.html'
    if request.method == 'POST':
        rack_form = RackSystemForm(request.POST)
        if rack_form.is_valid():
            new_system = rack_form.save(commit=False)
            new_system.system_rack = rack
            new_system.save()

            data['system'] = new_system
            resp_data['success'] = True
            template = 'systems/rack_row_partial.html'
        else:
            resp_data['success'] = False
    else:
        rack_form = RackSystemForm()

    data['form'] = rack_form
    data['rack'] = rack

    resp_data['payload'] = render_to_string(template, data, RequestContext(request)).strip(' ')

    return HttpResponse(json.dumps(resp_data), mimetype="application/json")

@allow_anyone
def racks_by_site(request, site_pk=0): # pylint: disable=unused-argument
    ret_list = []
    if int(site_pk) > 0:
        site = models.Site.objects.get(id=site_pk)
        l_racks = models.SystemRack.objects\
            .select_related('site')\
            .filter(site=site).order_by('name')
    else:
        l_racks = models.SystemRack.objects.select_related('site').order_by('site', 'name')

    for r in l_racks:
        ret_list.append({'name':'%s %s' % (r.site.full_name if r.site else '', r.name), 'id':r.id})
    return HttpResponse(json.dumps(ret_list))

@allow_anyone
def racks(request):
    from systems.forms import RackFilterForm
    filter_form = RackFilterForm(request.GET)

    l_racks = models.SystemRack.objects.select_related('site')

    system_query = Q()
    if 'site' in request.GET:
        site_id = request.GET['site']
        has_query = True
        if site_id and int(site_id) > 0:
            site = models.Site.objects.get(id=site_id)
            filter_form.fields['rack'].choices = [('', 'ALL')] + [
                (m.id, m.site.full_name + ' ' +  m.name)
                for m in models.SystemRack.objects.filter(site=site).order_by('name')
            ]
    else:
        has_query = False

    if filter_form.is_valid():
        if filter_form.cleaned_data['rack']:
            l_racks = l_racks.filter(id=filter_form.cleaned_data['rack'])
            has_query = True
        if filter_form.cleaned_data['site'] and int(filter_form.cleaned_data['site']) > 0:
            l_racks = l_racks.filter(site=filter_form.cleaned_data['site'])
            has_query = True
        filter_status = filter_form.cleaned_data['status']
        if filter_status:
            system_query &= Q(system_status=filter_form.cleaned_data['status'])
            has_query = True
        if not filter_form.cleaned_data['show_decommissioned']:
            decommissioned = models.SystemStatus.objects.get(status='decommissioned')
            system_query = system_query & ~Q(system_status=decommissioned)

    ##Here we create an object to hold decommissioned systems for the following filter
    if not has_query:
        l_racks = []
    else:
        l_racks = [(k, list(k.system_set.select_related(
            'server_model',
            'system_status',
        ).filter(system_query).order_by('-rack_order'))) for k in l_racks]

    return render_to_response('systems/racks.html', {
        'racks': l_racks,
        'filter_form': filter_form,
        'read_only': getattr(request, 'read_only', False),
        }, RequestContext(request))


class OperatingSystemDeleteView(DeleteView):
    model = models.OperatingSystem
    template_name = "generic_delete.html"
    fields = '__all__'

    def get_success_url(self):
        return reverse("operatingsystem-list")


class OperatingSystemCreateView(CreateView):
    model = models.OperatingSystem
    template_name = "systems/generic_form.html"
    fields = '__all__'

    def get_success_url(self):
        return reverse("operatingsystem-list")

class OperatingSystemEditView(UpdateView):
    model = models.OperatingSystem
    template_name = "systems/generic_form.html"
    fields = '__all__'

    def get_success_url(self):
        return reverse("operatingsystem-list")


class OperatingSystemListView(ListView):
    model = models.OperatingSystem
    template_name = "operating_system_list"

class SystemRevision(CompareMixin, UpdateView):
    template_name = "systems/revision_confirm_restore.html"
    model = Version
    fields = '__all__'
    compare_exclude = ['current_revision']

    def get_queryset(self):
        self.queryset = Version.objects.all()
        return self.queryset

    def post(self, request, pk=None): # pylint: disable=arguments-differ
        version = Version.objects.get(pk=pk)
        system = System.objects.get(pk=version.object_id)
        system.current_revision = pk
        system.save()
        version.revision.revert()
        return HttpResponseRedirect("/systems/show/{}/".format(version.object.id))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _id = self.kwargs['pk']
        version = Version.objects.get(pk=_id)
        system = System.objects.get(pk=version.object_id)
        if system.current_revision > 0:
            current = Version.objects.get(pk=system.current_revision)
        else:
            current = Version.objects.get_for_object(version.object).last()

        context['revision'] = version
        context['current'] = current
        compare = self.compare(version.object, current, version)[0]
        context['compare'] = compare
        return context

def rack_delete(request, object_id):
    from .models import SystemRack
    rack = get_object_or_404(SystemRack, pk=object_id)
    if request.method == "POST":
        rack.delete()
        return HttpResponseRedirect('/systems/racks/')
    else:
        return render_to_response('systems/rack_confirm_delete.html', {
            'rack': rack,
        }, RequestContext(request))


def rack_edit(request, object_id):
    rack = get_object_or_404(models.SystemRack, pk=object_id)
    from .forms import SystemRackForm
    if request.method == 'POST':
        form = SystemRackForm(request.POST, instance=rack)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/systems/racks/')
    else:
        form = SystemRackForm(instance=rack)

    return render_to_response(
        'systems/generic_form.html',
        {
            'form': form,
        },
        RequestContext(request))


def rack_new(request):
    from .forms import SystemRackForm
    initial = {}
    if request.method == 'POST':
        form = SystemRackForm(request.POST, initial=initial)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/systems/racks/')
    else:
        form = SystemRackForm(initial=initial)

    return render_to_response(
        'generic_form.html',
        {
            'form': form,
        },
        RequestContext(request))

def ajax_racks_by_site(request, site_pk):
    site = get_object_or_404(models.Site, pk=site_pk)
    decom = SystemStatus.objects.get(status='decommissioned')

    def filter_decom(system_Q):
        return system_Q.exclude(system_status=decom)

    return render(request, 'systems/rack_ajax_by_site.html', {
        'racks': site.systemrack_set.all(),
        'site': site,
        'systems': System.objects,
        'filter_decom': filter_decom
    })

def server_model_create(request):
    from .forms import ServerModelForm
    if request.method == 'POST':
        form = ServerModelForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/systems/server_models/')
    else:
        form = ServerModelForm()

    return render_to_response(
        'generic_form.html',
        {
            'form': form,
        },
        RequestContext(request))
def server_model_edit(request, object_id):
    server_model = get_object_or_404(models.ServerModel, pk=object_id)
    from systems.forms import ServerModelForm
    if request.method == 'POST':
        form = ServerModelForm(request.POST, instance=server_model)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/systems/server_models/')
    else:
        form = ServerModelForm(instance=server_model)

    return render_to_response(
        'generic_form.html',
        {
            'form': form,
        },
        RequestContext(request))


@csrf_exempt
def operating_system_create_ajax(request):
    if request.method == "POST":
        if 'name' in request.POST and 'version' in request.POST:
            name = request.POST['name']
            version = request.POST['version']
        models.OperatingSystem(name=name, version=version).save()
        return operating_system_list_ajax(request)
    else:
        return HttpResponse("OK")


@csrf_exempt
def server_model_create_ajax(request):
    if request.method == "POST":
        if 'model' in request.POST and 'vendor' in request.POST:
            model = request.POST['model']
            vendor = request.POST['vendor']
        models.ServerModel(vendor=vendor, model=model).save()
        return server_model_list_ajax(request)
    else:
        return HttpResponse("OK")


def operating_system_list_ajax(request):
    ret = []
    for m in models.OperatingSystem.objects.all():
        ret.append({'id': m.id, 'name': "%s - %s" % (m.name, m.version)})

    return HttpResponse(json.dumps(ret))


def server_model_list_ajax(request):
    ret = []
    for m in models.ServerModel.objects.all():
        ret.append({'id': m.id, 'name': "%s - %s" % (m.vendor, m.model)})

    return HttpResponse(json.dumps(ret))


def server_model_show(request, object_id):
    _object = get_object_or_404(models.ServerModel, pk=object_id)

    return render_to_response(
        'systems/servermodel_detail.html',
        {
            'object': _object,
        },
        RequestContext(request))


def server_model_list(request):
    object_list = models.ServerModel.objects.all()
    return render_to_response(
        'systems/servermodel_list.html',
        {
            'object_list': object_list,
        },
        RequestContext(request))


def csv_import(request):
    from .forms import CSVImportForm

    def generic_getter(field):
        return field

    def uppercase_getter(field):
        return field.upper()

    def system_status_getter(field):
        try:
            return models.SystemStatus.objects.get(status=field)
        except models.SystemStatus.DoesNotExist:
            return

    def server_model_getter(field):
        try:
            return models.ServerModel.objects.get(id=field)
        except models.ServerModel.DoesNotExist:
            return

    def rack_getter(field):
        try:
            return models.SystemRack.objects.get(name=field)
        except models.SystemRack.DoesNotExist:
            return None

    ALLOWED_COLUMNS = {
        'hostname': generic_getter,
        'asset_tag': generic_getter,
        'serial': uppercase_getter,
        'notes': generic_getter,
        'oob_ip': generic_getter,
        'system_status': system_status_getter,
        'system_rack': rack_getter,
        'rack_order': generic_getter,
        'server_model': server_model_getter,
        'purchase_price': generic_getter,
    }

    new_systems = 0
    if request.method == 'POST':
        form = CSVImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_reader = csv.reader(form.cleaned_data['csv'])
            headers = csv_reader.next()
            for line in csv_reader:
                cur_data = dict(zip(headers, line))

                system_data = dict(
                    (a, getter(cur_data.get(a, None)))
                    for a, getter in ALLOWED_COLUMNS.iteritems())

                s = models.System(**system_data)
                try:
                    s.full_clean()
                except ValidationError as exc:
                    print(exc)
                else:
                    s.save()
                    new_systems += 1
            form = None
    else:
        form = CSVImportForm()

    return render_to_response(
        'systems/csv_import.html',
        {
            'form': form,
            'allowed_columns': ALLOWED_COLUMNS,
            'new_systems': new_systems,
        },
        RequestContext(request))
