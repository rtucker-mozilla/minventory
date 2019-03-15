""" systems model """
import datetime
import re
import socket
import math
import string
import reversion
from reversion.signals import post_revision_commit
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.db.models.query import QuerySet
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.urls import reverse
from settings import BUG_URL


class Refresher(object):
    """ Mixin class. Make sure the mixer class is django ORM based class """
    def refresh(self):
        """
            refresh function which is probably useless in django 2.1
            @TODO: figure out if this does anything in modern django
        """

        return self.__class__.objects.get(pk=self.pk)


def create_key_index(key_values):
    """ return list of dict with key/value pairs """
    index = {}
    for key_value in key_values:
        index[key_value['key']] = key_value
    return index


class BaseKeyValue(models.Model):
    """ How this KeyValue class works:
        The KeyValue objects have functions that correspond to different
        keys. When a key is saved an attempt is made to find a validation
        function for that key.

        >>> attr = hasattr(kv, key)

        If `attr` is not None, then it is checked for callability.

        >>> attr = getattr(kv, key)
        >>> callable(attr)

        If it is callable, it is called with the value of the key.

        >>> kv.attr(kv.value)

        The validator is then free to raise exceptions if the value being
        inserted is invalid.

        When a validator for a key is not found, the KeyValue class can either
        riase an exception or not. This behavior is controled by the
        'force_validation' attribute: if 'force_validation' is 'True' and
        KeyValue requires a validation function. The 'require_validation' param
        to the clean method can be used to override the behavior of
        'force_validation'.

        Subclass this class and include a Foreign Key when needed.

        Validation functions can start with '_aa_'. 'aa' stands for auxililary
        attribute.
    """
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    force_validation = False

    class Meta:
        """ class Meta """
        abstract = True

    def __repr__(self):
        return "<{0}>".format(self)

    def __str__(self):
        return "Key: {0} Value {1}".format(self.key, self.value)

    @property
    def uri(self):
        """ returns link to update """
        return '/en-US/core/keyvalue/api/{0}/{1}/update/'.format(
            self.__class__.__name__.lower(), self.pk
        )

    def get_absolute_url(self):
        """ returns absolute_url """
        return '/en-US/core/keyvalue/{0}/{1}/'.format(
            self.__class__.__name__.lower(), self.obj.pk
        )

    def get_bundle(self):
        """ returns bundle of key/value """
        return {
            'key': self.key, 'value': self.value, 'uri': self.uri,
            'kv_pk': self.pk, 'obj_pk': self.obj.pk
        }

    def clean(self, require_validation=True, check_unique=True):  # pylint: disable=arguments-differ
        """ run clean """
        key_attr = self.key.replace('-', '_')
        # aa stands for auxilarary attribute.
        if (not hasattr(self, key_attr) and
                not hasattr(self, "_aa_" + key_attr)):
            # ??? Do we want this?
            if self.force_validation and require_validation:
                raise ValidationError("No validator for key %s" % self.key)
            else:
                if check_unique:  # Since we aren't call this later
                    self.validate_unique()
                return
        if hasattr(self, key_attr):
            validate = getattr(self, key_attr)
        else:
            validate = getattr(self, "_aa_" + key_attr)

        if not callable(validate):
            raise ValidationError("No validator for key %s not callable" %
                                  key_attr)
        try:
            validate()
        except TypeError as exc:
            # We want to catch when the validator didn't accept the correct
            # number of arguements.
            raise ValidationError("%s" % str(exc))
        if check_unique:
            self.validate_unique()

    def validate_unique(self): # pylint: disable=arguments-differ
        if (self.__class__.objects.filter(
                key=self.key, value=self.value, obj=self.obj).
                filter(~Q(id=self.pk)).exists()):
            raise ValidationError("A key with this value already exists.")

def validate_mac(mac):
    """
    Validates a mac address. If the mac is in the form XX-XX-XX-XX-XX-XX this
    function will replace all '-' with ':'.

    :param mac: The mac address
    :type mac: str
    :returns: The valid mac address.
    :raises: ValidationError
    """
    return mac

def validate_label(label, valid_chars=None):
    """Validate a label.
        :param label: The label to be tested.
        :type label: str
        "Allowable characters in a label for a host name are only ASCII
        letters, digits, and the '-' character."
        "Labels may not be all numbers, but may have a leading digit"
        "Labels must end and begin only with a letter or digit"
        -- `RFC <http://tools.ietf.org/html/rfc1912>`__
        "[T]he following characters are recommended for use in a host
        name: "A-Z", "a-z", "0-9", dash and underscore"
        -- `RFC <http://tools.ietf.org/html/rfc1033>`__
    """
    _name_type_check(label)

    if not valid_chars:
        # "Allowable characters in a label for a host name are only
        # ASCII letters, digits, and the `-' character." "[T]he
        # following characters are recommended for use in a host name:
        # "A-Z", "a-z", "0-9", dash and underscore"
        valid_chars = string.ascii_letters + "0123456789" + "-" + "_"

    # Labels may not be all numbers, but may have a leading digit TODO
    # Labels must end and begin only with a letter or digit TODO

    for char in label:
        if char == '.':
            raise ValidationError("Invalid name {0}. Please do not span "
                                  "multiple domains when creating records."
                                  .format(label))
        if valid_chars.find(char) < 0:
            raise ValidationError("Invalid name {0}. Character '{1}' is "
                                  "invalid.".format(label, char))

    end_chars = string.ascii_letters + "0123456789"

    if (
            label and
            not label.endswith(tuple(end_chars)) or
            # SRV records can start with '_'
            not label.startswith(tuple(end_chars + '_'))
    ):
        raise ValidationError(
            "Labels must end and begin only with a letter or digit"
        )

    return

def _name_type_check(name):
    if not isinstance(name, str):
        raise ValidationError("Error: A name must be of type str.")

def validate_name(fqdn):
    """Run test on a name to make sure that the new name is constructed
    with valid syntax.

        :param fqdn: The fqdn to be tested.
        :type fqdn: str


        "DNS domain names consist of "labels" separated by single dots."
        -- `RFC <http://tools.ietf.org/html/rfc1912>`__


        .. note::
            DNS name hostname grammar::

                <domain> ::= <subdomain> | " "

                <subdomain> ::= <label> | <subdomain> "." <label>

                <label> ::= <letter> [ [ <ldh-str> ] <let-dig> ]

                <ldh-str> ::= <let-dig-hyp> | <let-dig-hyp> <ldh-str>

                <let-dig-hyp> ::= <let-dig> | "-"

                <let-dig> ::= <letter> | <digit>

                <letter> ::= any one of the 52 alphabetic characters A
                through Z in upper case and a through z in lower case

                <digit> ::= any one of the ten digits 0 through 9

            --`RFC 1034 <http://www.ietf.org/rfc/rfc1034.txt>`__
    """
    _name_type_check(fqdn)

    # Star records are allowed. Remove them during validation.
    if fqdn[0] == '*':
        fqdn = fqdn[1:]
        fqdn = fqdn.strip('.')

    for label in fqdn.split('.'):
        if not label:
            raise ValidationError("Invalid name {0}. Empty label."
                                  .format(fqdn))
        validate_label(label)


class QuerySetManager(models.Manager):
    """ manager """
    def get_query_set(self):
        """ return the default queryset """
        return self.model.QuerySet(self.model)


def to_a(text, obj, use_absolute_url=True):
    """ convert to string """
    if use_absolute_url:
        return "<a href='{0}'>{1}</a>".format(obj.get_absolute_url(), text)
    else:
        return "<a href='{0}'>{1}</a>".format(obj, text)

class DirtyFieldsMixin(object):
    """ mixin to detect fields that are dirty """
    def __init__(self, *args, **kwargs):
        super(DirtyFieldsMixin, self).__init__(*args, **kwargs)
        post_save.connect(
            self._reset_state, sender=self.__class__,
            dispatch_uid='{0}-DirtyFieldsMixin-sweeper'.format(
                self.__class__.__name__)
        )
        self._reset_state()

    def _reset_state(self, **kwargs): # pylint: disable=unused-argument
        self._original_state = self._as_dict()

    def _as_dict(self):
        return dict([
            (f.attname, getattr(self, f.attname))
            for f in self._meta.local_fields
        ])

    def get_dirty_fields(self):
        new_state = self._as_dict()
        return dict([
            (key, value) for key, value
            in self._original_state.iteritems() if value != new_state[key]
        ])


class BuildManager(models.Manager):
    def get_query_set(self):
        return super(BuildManager, self).get_query_set().filter(
            allocation__name='release'
        )


class SystemWithRelatedManager(models.Manager):
    def get_query_set(self):
        objects = super(SystemWithRelatedManager, self).get_query_set()
        return objects.select_related(
            'operating_system',
            'server_model',
            'system_rack',
        )

def validate_site_name(name):
    if not name:
        raise ValidationError("A site name must be non empty.")
    if name.find(' ') > 0:
        raise ValidationError("A site name must not contain spaces.")
    if name.find('.') > 0:
        raise ValidationError("A site name must not contain a period.")

class Site(models.Model):
    systems = None
    # This is memoized later. Remove it when SystemRack is moved into it's own
    # file as this circular import is not required.

    id = models.AutoField(primary_key=True)
    full_name = models.CharField(
        max_length=255, null=True, blank=True
    )
    name = models.CharField(
        max_length=255, validators=[validate_site_name], blank=True
    )
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)

    search_fields = ('full_name',)

    template = (
        "{full_name:$lhs_just} {rdtype:$rdtype_just} {full_name:$rhs_just}"
    )

    class Meta:
        db_table = 'site'
        unique_together = ('full_name',)

    def __str__(self):
        return "{0}".format(self.full_name)

    def __repr__(self):
        return "<Site {0}>".format(self)

    @classmethod
    def get_api_fields(cls):
        return ['name', 'parent', 'full_name']

    @property
    def rdtype(self):
        return 'SITE'

    def save(self, *args, **kwargs): # pylint: disable=arguments-differ
        self.name = self.full_name.split('.')[0]
        self.full_clean()
        super(Site, self).save(*args, **kwargs)

    def clean(self):
        map(validate_site_name, self.full_name.split('.'))
        self.name, parent_name = (
            self.full_name.split('.')[0], self.full_name.split('.')[1:]
        )
        validate_site_name(self.name)
        if self.pk:
            db_self = self.__class__.objects.get(pk=self.pk)
            if self.site_set.exists() and self.name != db_self.name:
                raise ValidationError(
                    "This site has child sites. You cannot change it's name "
                    "without affecting all child sites."
                )
        if self.full_name.find('.') != -1:
            self.parent, _ = self.__class__.objects.get_or_create(
                full_name='.'.join(parent_name)
            )
        else:
            self.parent = None

    def delete(self, *args, **kwargs): # pylint: disable=arguments-differ
        if self.site_set.all().exists():
            raise ValidationError(
                "This site has child sites. You cannot delete it."
            )
        super(Site, self).delete(*args, **kwargs)

    def details(self):
        details = [
            ('Name', self.full_name),
        ]
        if self.parent:
            details.append(
                ('Parent Site', to_a(self.parent.full_name, self.parent))
            )
        else:
            details.append(
                ('All sites', to_a('Global Site View', reverse('site-list'),
                                   use_absolute_url=False))
            )
        return details

    def get_site_path(self):
        target = self
        npath = [self.name]
        while True:
            if target.parent is None:
                break
            else:
                npath.append(target.parent.name)
                target = target.parent
        return '.'.join(npath)

    def get_systems(self):
        """Get all systems associated to racks in this site"""
        if not self.systems:
            self.systems = System.objects.all()
        return self.systems.filter(system_rack__in=self.systemrack_set.all())

class ScheduledTask(models.Model):
    task = models.CharField(max_length=255, blank=False, unique=True)
    type = models.CharField(max_length=255, blank=False)
    objects = QuerySetManager()

    class QuerySet(QuerySet):
        def delete_all_reverse_dns(self):
            self.filter(type='reverse_dns_zone').delete()

        def delete_all_dhcp(self):
            self.filter(type='dhcp').delete()

        def dns_tasks(self):
            return self.filter(type='dns')

        def get_all_dhcp(self):
            return self.filter(type='dhcp')

        def get_all_reverse_dns(self):
            return self.filter(type='reverse_dns_zone')

        def get_next_task(self, atype=None):
            if atype is not None:
                try:
                    return self.filter(type=atype)[0]
                except: # pylint: disable=bare-except
                    return None
            else:
                return None

        def get_last_task(self, atype=None):
            if atype is not None:
                try:
                    return self.filter(type=atype)[-1]
                except:  # pylint: disable=bare-except
                    return None
            else:
                return None

    class Meta:
        db_table = u'scheduled_tasks'
        ordering = ['task']


class Contract(models.Model):
    contract_number = models.CharField(max_length=255, blank=True)
    support_level = models.CharField(max_length=255, blank=True)
    contract_link = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    expiration = models.DateTimeField(null=True, blank=True)
    system = models.ForeignKey('System', on_delete=models.CASCADE)
    created_on = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = u'contracts'


class Location(models.Model):
    name = models.CharField(unique=True, max_length=255, blank=True)
    address = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = u'locations'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '/systems/locations/show/{0}/'.format(self.pk)

    def get_edit_url(self):
        return self.get_absolute_url()


class PortData(models.Model):
    ip_address = models.CharField(max_length=15, blank=True)
    port = models.IntegerField(blank=True)
    protocol = models.CharField(max_length=3, blank=True)
    state = models.CharField(max_length=13, blank=True)
    service = models.CharField(max_length=64, blank=True)
    version = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.ip_address

    class Meta:
        db_table = u'port_data'


class AdvisoryData(models.Model):
    ip_address = models.CharField(max_length=15, blank=True)
    advisory = models.TextField(blank=True)
    title = models.TextField(blank=True)
    severity = models.FloatField(blank=True)
    references = models.TextField(blank=True)

    class Meta:
        db_table = u'advisory_data'

    def __str__(self):
        return self.ip_address


class ApiManager(models.Manager):
    def get_query_set(self):
        results = super(ApiManager, self).get_query_set()
        return results


class KeyValue(BaseKeyValue):
    obj = models.ForeignKey('System', null=True, on_delete=models.CASCADE)
    objects = models.Manager()
    expanded_objects = ApiManager()

    class Meta:
        db_table = u'key_value'

    def __str__(self):
        return self.key if self.key else ''

    def __repr__(self):
        return "<{0}: '{1}'>".format(self.key, self.value)

    def save(self, *args, **kwargs): # pylint: disable=arguments-differ
        if re.match(r'^nic\.\d+\.mac_address\.\d+$', self.key):
            self.value = self.value.replace('-', ':')
            self.value = validate_mac(self.value)
        if self.key is None:
            self.key = ''
        if self.value is None:
            self.value = ''
        super(KeyValue, self).save(*args, **kwargs)


class NetworkAdapter(models.Model):
    system_id = models.IntegerField()
    mac_address = models.CharField(max_length=255)
    ip_address = models.CharField(max_length=255)
    adapter_name = models.CharField(max_length=255)
    system_id = models.CharField(max_length=255)
    switch_port = models.CharField(max_length=128)
    filename = models.CharField(max_length=64)
    option_host_name = models.CharField(max_length=64)
    option_domain_name = models.CharField(max_length=128)
    switch_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = u'network_adapters'

    def save(self, *args, **kwargs): # pylint: disable=arguments-differ
        self.full_clean()  # Calls field.clean() on all fields.
        super(NetworkAdapter, self).save(*args, **kwargs)

    def get_system_host_name(self):
        systems = System.objects.filter(id=self.system_id)
        if systems:
            for system in systems:
                return system.hostname
        else:
            return ''


class Mac(models.Model):
    system = models.ForeignKey('System', on_delete=models.CASCADE)
    mac = models.CharField(unique=True, max_length=17)

    class Meta:
        db_table = u'macs'


@reversion.register
class OperatingSystem(models.Model):
    name = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = u'operating_systems'
        ordering = ['name', 'version']

    def __str__(self):
        return "%s - %s" % (self.name, self.version)

    @classmethod
    def get_api_fields(cls):
        return ('name', 'version')


@reversion.register
class ServerModel(models.Model):
    vendor = models.CharField(max_length=255, blank=True)
    model = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True, null=True)
    part_number = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = u'server_models'
        ordering = ['vendor', 'model']

    def __str__(self):
        return u"%s - %s" % (self.vendor, self.model)

    @classmethod
    def get_api_fields(cls):
        return ('vendor', 'model', 'part_number', 'description')


@reversion.register
class SystemRack(models.Model):
    name = models.CharField(max_length=255)
    location = models.ForeignKey('Location', null=True, on_delete=models.CASCADE)
    site = models.ForeignKey('Site', null=True, on_delete=models.CASCADE)

    search_fields = ('name', 'site__name')

    class Meta:
        db_table = u'system_racks'
        ordering = ['name']
        unique_together = ('name', 'site',)

    def __str__(self):
        return "%s" % (
            #self.name, self.site.full_name if self.site else ''
            self.name
        )

    @classmethod
    def get_api_fields(cls):
        return ('name', 'location', 'site')

    def get_absolute_url(self):
        return '/en-US/systems/racks/?rack={0}'.format(self.pk)

    def get_edit_url(self):
        return '/en-US/systems/racks/edit/{0}/'.format(self.pk)

    def delete(self, *args, **kwargs): # pylint: disable=arguments-differ
        self.system_set.clear()
        super(SystemRack, self).delete(*args, **kwargs)

    def systems(self):
        return self.system_set.select_related().order_by('rack_order')


@reversion.register
class SystemType(models.Model):
    type_name = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = u'system_types'

    def __str__(self):
        return self.type_name

    @classmethod
    def get_api_fields(cls):
        return ('type_name',)


@reversion.register
class SystemStatus(models.Model):
    status = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=255, blank=True)
    color_code = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = u'system_statuses'
        ordering = ['status']

    def __str__(self):
        return self.status

    @classmethod
    def get_api_fields(cls):
        return ('status',)

@reversion.register(follow= # pylint: disable=function-redefined
                    [
                        "system_type",
                        "operating_system",
                        "system_status",
                        "server_model",
                        "system_rack"
                    ]
                    )
class System(Refresher, DirtyFieldsMixin, models.Model):

    YES_NO_CHOICES = (
        (0, 'No'),
        (1, 'Yes'),
    )

    # Related Objects
    operating_system = models.ForeignKey(
        'OperatingSystem', blank=True, null=True, on_delete=models.SET_NULL)
    system_type = models.ForeignKey('SystemType', blank=True, null=True, on_delete=models.CASCADE)
    system_status = models.ForeignKey(
        'SystemStatus',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )
    server_model = models.ForeignKey('ServerModel', blank=True, null=True, on_delete=models.CASCADE)
    system_rack = models.ForeignKey('SystemRack', blank=True, null=True, on_delete=models.CASCADE)

    hostname = models.CharField(
        unique=True, max_length=255, validators=[validate_name]
    )
    serial = models.CharField(max_length=255, blank=True, null=True)
    pdu1 = models.CharField(max_length=255, blank=True, null=True)
    pdu2 = models.CharField(max_length=255, blank=True, null=True)
    created_on = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(null=True, blank=True)
    oob_ip = models.CharField(max_length=30, blank=True, null=True)
    asset_tag = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    licenses = models.TextField(blank=True, null=True)
    rack_order = models.DecimalField(
        null=True, blank=True, max_digits=6, decimal_places=2)
    switch_ports = models.CharField(max_length=255, blank=True, null=True)
    patch_panel_port = models.CharField(max_length=255, blank=True, null=True)
    oob_switch_port = models.CharField(max_length=255, blank=True, null=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.CharField(max_length=255, blank=True, null=True)
    change_password = models.DateTimeField(null=True, blank=True)
    ram = models.CharField(max_length=255, blank=True, null=True)
    warranty_start = models.DateField(blank=True, null=True, default=None)
    warranty_end = models.DateField(blank=True, null=True, default=None)
    current_revision = models.IntegerField(default=0)

    objects = models.Manager()
    build_objects = BuildManager()
    with_related = SystemWithRelatedManager()

    search_fields = (
        "hostname", "serial", "notes", "asset_tag",
        "oob_ip", "system_rack__site__full_name", "system_rack__name"
    )

    template = (
        "{hostname:$lhs_just} {oob_ip_str:$rdtype_just} INV "
        "{rdtype:$rdtype_just} {asset_tag_str} {serial_str}"
    )

    class Meta:
        db_table = u'systems'

    def __str__(self):
        return self.hostname

    @classmethod
    def get_api_fields(cls):
        return [
            'operating_system', 'server_model', 'system_rack',
            'system_type', 'system_status', 'hostname', 'serial', 'oob_ip',
            'asset_tag', 'notes', 'rack_order', 'switch_ports',
            'patch_panel_port', 'oob_switch_port', 'purchase_date',
            'purchase_price', 'change_password', 'warranty_start',
            'warranty_end',
        ]

    @property
    def primary_ip(self):
        try:
            first_ip = self.keyvalue_set.filter(
                key__contains='ipv4_address').order_by('key')[0].value
            return first_ip
        except: # pylint: disable=bare-except
            return None

    @property
    def primary_reverse(self):
        try:
            return str(socket.gethostbyaddr(self.primary_ip)[0])
        except: # pylint: disable=bare-except
            return None

    @property
    def notes_with_link(self):
        if not self.notes:
            return ''
        notes = self.notes
        pattern = r'([bB]ug#?\D#?(\d+))'
        matches = re.findall(pattern, notes)
        for raw_text, bug_number in matches:
            bug_url = '<a href="{0}{1}">{2}</a>'.format(
                BUG_URL, bug_number, raw_text
            )
            notes = notes.replace(raw_text, bug_url, 1)
        return notes

    @classmethod
    def field_names(cls):
        return [field.name for field in cls._meta.fields]

    @classmethod
    def rack_ordering(cls, systems):
        """
        A generator that sorts the systems by whole rack_order value (in
        descending order) and then sub sorts the decimal part of rack_order in
        ascending order.

        I.e.
        45.00
        44.00
        43.00
        31.00
        31.01
        31.02
        21.00
        11.01
        11.02
        11.03
        11.04
        1.00

        (See bug 999204)
        """
        if isinstance(systems, QuerySet):
            systems = list(systems)

        systems = list(reversed(sorted(systems, key=lambda s: s.rack_order)))
        i = 0
        cur_integer = None

        while True:
            if i >= len(systems):
                break

            if systems[i].rack_order is None:
                yield systems[i]
                i += 1
                continue

            cur_integer = math.floor(systems[i].rack_order)

            j = i

            while (
                    (j + 1) < len(systems) and
                    systems[j + 1].rack_order is not None and
                    math.floor(systems[j + 1].rack_order) == cur_integer
            ):
                j += 1

            new_i = j + 1

            while j >= i:
                yield systems[j]
                j -= 1

            i = new_i

    @classmethod
    def get_bulk_action_list(cls, query, fields=None, show_related=True):
        """
        Return a list of serialized system objects and their related objects to
        be used in the bulk_action api.

        This function will serialize and export StaticReg objects and their
        accompanying HWAdapter objects
        """
        if not fields:
            fields = cls.get_api_fields() + ['pk']

        # Pull in all system blobs and tally which pks we've seen. In one swoop
        # pull in all staticreg blobs and put them with their systems.
        sys_t_bundles = cls.objects.filter(query).values_list(*fields)

        sys_d_bundles = {}
        sys_pks = []
        for t_bundle in sys_t_bundles:
            d_bundle = dict(zip(fields, t_bundle))
            system_hostname = d_bundle['hostname']
            sys_d_bundles[system_hostname] = d_bundle
            sys_d_bundles[system_hostname]['keyvalue_set'] = create_key_index(
                cls.keyvalue_set.related.model.objects.filter(
                    obj=d_bundle['pk']
                ).values('key', 'value', 'pk')
            )
            if show_related:
                sys_pks.append(d_bundle['pk'])

        sys_q = Q(system__in=sys_pks)

        # Note that CNAMEs are pulled in during this call
        sreg_bundles = cls.staticreg_set.related.model.get_bulk_action_list(
            sys_q
        )

        hw_q = Q(sreg__system__in=sys_pks)
        hw_bundles = (
            cls.staticreg_set.related.model.
            hwadapter_set.related.model.get_bulk_action_list(hw_q)
        )

        # JOIN staticreg, hw_adapter ON sreg_pk
        for sreg_pk, hw_bundle in hw_bundles.iteritems():
            sreg_bundles[sreg_pk]['hwadapter_set'] = hw_bundle

        for sreg_pk, sreg_bundle in sreg_bundles.iteritems():
            system = sreg_bundle.pop('system__hostname')
            sys_d_bundles[system].setdefault(
                'staticreg_set', {}
            )[sreg_bundle['name']] = sreg_bundle

        return sys_d_bundles

    @property
    def rdtype(self):
        return 'SYS'

    def bind_render_record(self, **kwargs): # pylint: disable=unused-argument
        data = {
            'oob_ip_str': self.oob_ip or 'None',
            'asset_tag_str': self.asset_tag or 'None',
            'serial_str': self.serial or 'None'
        }
        return super(System, self).bind_render_record(**data)

    def save(self, *args, **kwargs): # pylint: disable=arguments-differ
        #self.save_history(kwargs)
        self.full_clean()
        with reversion.create_revision():
            request = kwargs.pop('request', None)
            if request:
                try:
                    if not request.user.is_anonymous:
                        reversion.set_user(request.user)
                except (ValueError, AttributeError):
                    # No user set
                    pass
            super(System, self).save(*args, **kwargs)

    def clean(self):
        # Only do this validation on new systems. Current data is so poor that
        # requireing existing systems to have this data is impossible
        if self.pk:
            return

        if not self.is_vm():
            self.validate_warranty()
            #self.validate_serial()

        if not self.system_status:
            self.system_status, _ = SystemStatus.objects.get_or_create(
                status='building'
            )

    def is_vm(self):
        """ this might have had value before but probably not anymore
                if not self.system_type:
                    return False

                return (
                    False if self.system_type.type_name.find('Virtual Server') == -1
                    else True
                )
        """
        return False


    def validate_system_type(self):
        if not self.system_type:
            raise ValidationError(
                "Server Type is a required field"
            )

    def validate_serial(self):
        if not self.serial:
            raise ValidationError(
                "Serial numbers are reruied for non VM systems"
            )

    def validate_warranty(self):
        # If pk is None we are a new system. New systems are required to have
        # their warranty data set
        if self.pk is None and not bool(self.warranty_end):
            raise ValidationError(
                "Warranty Data is required for non virtual systems"
            )

        if bool(self.warranty_start) ^ bool(self.warranty_end):
            raise ValidationError(
                "Warranty must have a start and end date"
            )

        if not self.warranty_start:
            return

        if self.warranty_start.timetuple() > self.warranty_end.timetuple():
            raise ValidationError(
                "warranty start date should be before the end date"
            )

    def save_history(self, kwargs):
        request = kwargs.pop('request', None)
        try:
            changes = self.get_dirty_fields()
            if changes:
                system = System.objects.get(id=self.id)
                save_string = ''
                for k, v in changes.items():
                    if k == 'system_status_id':
                        k = 'System Status'
                        ss = SystemStatus.objects.get(id=v)
                        v = ss
                    if k == 'operating_system_id':
                        k = 'Operating System'
                        ss = OperatingSystem.objects.get(id=v)
                        v = ss
                    if k == 'server_model_id':
                        k = 'Server Model'
                        ss = ServerModel.objects.get(id=v)
                        v = ss
                    save_string += '%s: %s\n\n' % (k, v)
                try:
                    remote_user = request.META['REMOTE_USER']
                except Exception: #pylint: disable=broad-except
                    remote_user = 'changed_user'
                tmp = SystemChangeLog(
                    system=system,
                    changed_by=remote_user,
                    changed_text=save_string,
                    changed_date=datetime.datetime.now()
                )
                tmp.save()
        except Exception: #pylint: disable=broad-except
            pass

        if not self.pk:
            self.created_on = datetime.datetime.now()

        self.updated_on = datetime.datetime.now()

    def get_edit_url(self):
        return "/systems/edit/{0}/".format(self.pk)

    def get_absolute_url(self):
        return "/systems/show/{0}/".format(self.pk)

    def get_next_key_value_adapter(self):
        """
            Return the first found adapter from the
            key value store. This will go away,
            once we are on the StaticReg
            based system
        """
        ret = {}
        ret['mac_address'] = None
        ret['ip_address'] = None
        ret['num'] = None
        ret['dhcp_scope'] = None
        ret['name'] = 'nic0'
        key_value = self.keyvalue_set.filter(
            key__startswith='nic', key__icontains='mac_address')[0]
        m = re.search(r'nic\.(\d+)\.mac_address\.0', key_value.key)
        ret['num'] = int(m.group(1))
        key_value_set = self.keyvalue_set.filter(
            key__startswith='nic.%s' % ret['num'])
        if not key_value_set:
            for kv in key_value_set:
                m = re.search(r'nic\.\d+\.(.*)\.0', kv.key)
                if m:
                    ret[m.group(1)] = str(kv.value)
            return ret
        else:
            return False

    def delete_key_value_adapter_by_index(self, index):
        """
            Delete a set of key_value items by index
            if index = 0
            delete where keyvalue.name startswith nic.0
        """
        self.keyvalue_set.filter(key__startswith='nic.%i' % index).delete()
        return True

    def external_data_conflict(self, attr):
        if not hasattr(self, attr):
            return False

        val = getattr(self, attr)
        if not val:
            return False

        for ed in self.externaldata_set.filter(name=attr):
            if (attr == 'oob_ip' and
                    ed.data == val.strip().lstrip('ssh').strip()):
                return False
            elif ed.data.upper() != val.upper():
                return True

        return False

    def get_updated_fqdn(self):
        allowed_domains = [
            'mozilla.com',
            'scl3.mozilla.com',
            'phx.mozilla.com',
            'phx1.mozilla.com',
            'mozilla.net',
            'mozilla.org',
            'build.mtv1.mozilla.com',
            'build.mozilla.org',
        ]
        reverse_fqdn = self.primary_reverse
        if self.primary_ip and reverse_fqdn:
            current_hostname = str(self.hostname)

            if current_hostname and current_hostname != reverse_fqdn:
                res = reverse_fqdn.replace(current_hostname, '').strip('.')
                if res in allowed_domains:
                    self.update_host_for_migration(reverse_fqdn)
        elif not self.primary_ip or self.primary_reverse:
            for domain in allowed_domains:
                updated = False
                if not updated:
                    try:
                        fqdn = socket.gethostbyaddr(
                            '%s.%s' % (self.hostname, domain)
                        )
                        if fqdn:
                            self.update_host_for_migration(fqdn[0])
                            updated = True
                    except Exception: #pylint: disable=broad-except
                        pass
            if not updated:
                pass
                #print "Could not update hostname %s" % (self.hostname)

    def update_host_for_migration(self, new_hostname):
        if new_hostname.startswith(self.hostname):
            kv = KeyValue(
                obj=self, key='system.hostname.alias.0', value=self.hostname
            )
            kv.save()
            try:
                self.hostname = new_hostname
                self.save()
            except Exception as exc: #pylint: disable=broad-except
                print("ERROR - {}".format(exc))

    def get_switches(self):
        return System.objects.filter(is_switch=1)

    def check_for_adapter(self, adapter_id):
        adapter_id = int(adapter_id)
        if adapter_id in self.get_adapter_numbers():
            return True
        return False

    def check_for_adapter_name(self, adapter_name):
        adapter_name = str(adapter_name)
        if adapter_name in self.get_nic_names():
            return True
        return False

    def get_nic_names(self):
        adapter_names = []
        pairs = KeyValue.objects.filter(
            obj=self, key__startswith='nic', key__contains='adapter_name'
        )
        for row in pairs:
            m = re.match(r'^nic\.\d+\.adapter_name\.\d+', row.key)
            if m:
                adapter_names.append(str(row.value))
        return adapter_names

    def get_adapter_numbers(self):
        nic_numbers = []
        pairs = KeyValue.objects.filter(obj=self, key__startswith='nic')
        for row in pairs:
            m = re.match(r'^nic\.(\d+)\.', row.key)
            if m:
                match = int(m.group(1))
                if match not in nic_numbers:
                    nic_numbers.append(match)
        return nic_numbers

    def get_adapter_count(self):
        return len(self.get_adapter_numbers())


class SystemChangeLog(models.Model):
    changed_by = models.CharField(max_length=255)
    changed_date = models.DateTimeField()
    changed_text = models.TextField()
    system = models.ForeignKey(System, on_delete=models.CASCADE)

    class Meta:
        db_table = u'systems_change_log'


class UserProfile(models.Model):
    PAGER_CHOICES = (
        ('epager', 'epager'),
        ('sms', 'sms'),
    )
    user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE)

    is_desktop_oncall = models.BooleanField()
    is_sysadmin_oncall = models.BooleanField()
    is_services_oncall = models.BooleanField()
    is_mysqldba_oncall = models.BooleanField()
    is_pgsqldba_oncall = models.BooleanField()
    is_netop_oncall = models.BooleanField()
    is_metrics_oncall = models.BooleanField()

    current_desktop_oncall = models.BooleanField()
    current_sysadmin_oncall = models.BooleanField()
    current_services_oncall = models.BooleanField()
    current_mysqldba_oncall = models.BooleanField()
    current_pgsqldba_oncall = models.BooleanField()
    current_netop_oncall = models.BooleanField()
    current_metrics_oncall = models.BooleanField()

    irc_nick = models.CharField(max_length=128, null=True, blank=True)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    pager_type = models.CharField(
        choices=PAGER_CHOICES, max_length=255, null=True, blank=True
    )
    pager_number = models.CharField(max_length=255, null=True, blank=True)
    epager_address = models.CharField(max_length=255, null=True, blank=True)
    objects = QuerySetManager()

    class Meta:
        db_table = u'user_profiles'

    def __str__(self):
        return "{0}".format(self.user.username)

    def __repr__(self):
        return "<UserProfile {0}>".format(self.user.username)

    class QuerySet(QuerySet):
        def get_all_desktop_oncall(self):
            self.filter(is_desktop_oncall=1)

        def get_current_desktop_oncall(self):
            self.filter(current_desktop_oncall=1).select_related()

        def get_all_services_oncall(self):
            self.filter(is_services_oncall=1)

        def get_current_services_oncall(self):
            self.filter(current_services_oncall=1).select_related()

        def get_all_sysadmin_oncall(self):
            self.filter(is_sysadmin_oncall=1)

        def get_current_sysadmin_oncall(self):
            self.filter(current_sysadmin_oncall=1).select_related()

        def get_all_metrics_oncall(self):
            self.filter(is_metrics_oncall=1)

        def get_current_metrics_oncall(self):
            self.filter(current_metrics_oncall=1).select_related()

@receiver(post_revision_commit)
def on_revision_commit(sender, **kwargs): # pylint: disable=unused-argument
    revision = kwargs['revision']
    try:
        system = System.objects.get(pk=kwargs['versions'][0].object.id)
        system.current_revision = revision.version_set.all().last().id
        system.save()
    except: # pylint: disable=bare-except
        return
