from django.db import models
from systems.models import OperatingSystem, ServerModel
from datetime import datetime, timedelta

# Create your models here.
class UnmanagedSystem(models.Model):
    serial = models.CharField(max_length=255, blank=True)
    asset_tag = models.CharField(max_length=255, blank=True)
    operating_system = models.ForeignKey(OperatingSystem, blank=True, null=True)
    owner = models.ForeignKey('Owner', blank=True, null=True)
    server_model = models.ForeignKey(ServerModel, blank=True, null=True)
    created_on = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(null=True, blank=True)
    date_purchased = models.DateField(null=True, blank=True)
    cost = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    search_fields = (
            'serial', 
            'asset_tag',
            'owner__name',
            'server_model__vendor',
            'notes',
            'server_model__model'
        )

    def __unicode__(self):
        try:
            server_model = self.server_model
        except ServerModel.DoesNotExist:
            server_model = ""
        return "%s - %s - %s" % (server_model, self.asset_tag, self.serial) 

    @models.permalink
    def get_absolute_url(self):
        return ('user-system-show', [self.id])

    class Meta:
        db_table = u'unmanaged_systems'

class History(models.Model):
    change = models.CharField(max_length=1000)
    system = models.ForeignKey(UnmanagedSystem)
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        "%s: %s" % (self.created, self.change)

    class Meta:
        ordering = ['-created']

class Owner(models.Model):
    name = models.CharField(unique=True, max_length=255, blank=True)
    address = models.TextField(blank=True)
    note = models.TextField(blank=True)
    user_location = models.ForeignKey('UserLocation', blank=True, null=True)
    email = models.CharField(max_length=255, blank=True)

    search_fields = (
            'name',
            'note',
            'email',
            )

    def __unicode__(self):
        return self.name

    def upgradeable_systems(self):
        return self.unmanagedsystem_set.filter(
            date_purchased__lt=datetime.now() - timedelta(days=730))

    @models.permalink
    def get_absolute_url(self):
        return ('owner-show', [self.id])

    def delete(self):
        UserLicense.objects.filter(owner=self).update(owner=None)
        UnmanagedSystem.objects.filter(owner=self).update(owner=None)
        super(Owner, self).delete()

    class Meta:
        db_table = u'owners'
        ordering = ['name']

class UserLicense(models.Model):
    username = models.CharField(max_length=255, blank=True)
    version = models.CharField(max_length=255, blank=True)
    license_type = models.CharField(max_length=255, blank=True)
    license_key = models.CharField(max_length=255, blank=True)
    owner = models.ForeignKey('Owner', blank=True, null=True)
    search_fields = (
            'username', 
            'version',
            'license_type',
            'license_key',
            'owner__name'
        )

    def __unicode__(self):
        return "%s - %s" % (self.license_type, self.license_key)

    class Meta:
        db_table = u'user_licenses'
        ordering = ['license_type']

class UserLocation(models.Model):
    city = models.CharField(unique=True, max_length=255, blank=True)
    country = models.CharField(unique=True, max_length=255, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return "%s - %s" % (self.city, self.country)

    class Meta:
        db_table = u'user_locations'