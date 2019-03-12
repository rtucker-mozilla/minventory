from systems import models
from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from dateutil.relativedelta import relativedelta
from systems.models import System
from django.http import Http404

from rest_framework import serializers
import datetime

class WarrantyStartField(serializers.Field):
    def to_representation(self, value):
        return "{}".format(value)

    def to_internal_value(self, data):
        if data != '':
            return datetime.datetime.strptime(data, "%Y-%m-%d")


class WarrantyEndField(serializers.Field):
    def to_representation(self, value):
        return "{}".format(value)

    def to_internal_value(self, data):
        if data != '':
            return datetime.datetime.strptime(data, "%Y-%m-%d")


class ServerModelTypeField(serializers.Field):
    def to_representation(self, value):
        return "{}-{}".format(value.vendor, value.model)

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.ServerModel.objects.get(pk=pk_int)
        except (models.ServerModel.DoesNotExist, ValueError):
            obj = None
        if obj is None:
            try:
                vendor = str(data.split("-")[0]).strip()
                model = str("-".join(data.split("-")[1:])).strip()
                obj = models.ServerModel.objects.filter(vendor=vendor,model=model).first()
            except models.ServerModel.DoesNotExist:
                obj = None
        if obj is None:
            try:
                vendor = str(data.split("-")[0]).strip()
                model = str("-".join(data.split("-")[1:])).strip()
                obj = models.ServerModel.objects.filter(model=model).first()
            except models.ServerModel.DoesNotExist:
                obj = None
        if obj is None:
            tmp = data
            obj = models.ServerModel.objects.create(vendor=tmp,model=tmp).save()
        if not obj:
            raise serializers.ValidationError(
                "Unable to find ServerModel {}".format(data),
                code=400
            )
        else:
            return obj
class OperatingSystemTypeField(serializers.Field):
    def to_representation(self, value):
        return "{}-{}".format(value.name, value.version)

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.OperatingSystem.objects.get(pk=pk_int)
        except (models.OperatingSystem.DoesNotExist, ValueError):
            pass
        try:
            name = data.split("-")[0]
            version = "-".join(data.split("-")[1:])
            obj = models.OperatingSystem.objects.get(name=name, version=version)
        except models.OperatingSystem.DoesNotExist:
            pass
        if not obj:
            raise serializers.ValidationError(
                "Unable to find OperatingSystem {}".format(data),
                code=400
            )
        else:
            return obj

class SystemTypeField(serializers.Field):
    def to_representation(self, value):
        return value.type_name

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.SystemType.objects.get(pk=pk_int)
        except (models.SystemType.DoesNotExist, ValueError):
            pass
        try:
            obj = models.SystemType.objects.get(type_name=data)
        except models.SystemType.DoesNotExist:
            pass
        if not obj:
            raise serializers.ValidationError(
                "Unable to find SystemType {}".format(data),
                code=400
            )
        else:
            return obj

class SystemStatusField(serializers.Field):
    def to_representation(self, value):
        return value.status

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.SystemStatus.objects.get(pk=pk_int)
        except (models.SystemStatus.DoesNotExist, ValueError):
            pass
        try:
            obj = models.SystemStatus.objects.get(status=data)
        except models.SystemStatus.DoesNotExist:
            pass
        if not obj:
            raise serializers.ValidationError(
                "Unable to find SystemStatus {}".format(data),
                code=400
            )
        else:
            return obj

class AllocationField(serializers.Field):
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.Allocation.objects.get(pk=pk_int)
        except (models.Allocation.DoesNotExist, ValueError):
            pass
        try:
            obj = models.Allocation.objects.get(name=data)
        except models.Allocation.DoesNotExist:
            pass
        if not obj:
            raise serializers.ValidationError(
                "Unable to find Allocation {}".format(data),
                code=400
            )
        else:
            return obj

class SystemRackField(serializers.Field):
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        obj = None
        try:
            pk_int = int(data)
            obj = models.SystemRack.objects.get(pk=pk_int)
        except (models.SystemRack.DoesNotExist, ValueError):
            pass
        try:
            obj = models.SystemRack.objects.filter(name=data).first()
        except models.SystemRack.DoesNotExist:
            pass
        if not obj:
            raise serializers.ValidationError(
                "Unable to find SystemRack {}".format(data),
                code=400
            )
        else:
            return obj

class SiteField(serializers.Field):
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        try:
            pk_int = int(data)
            return models.Site.objects.get(pk=pk_int)
        except (models.Site.DoesNotExist, ValueError):
            return models.Site.objects.get(name=data)




class PatchModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        kwargs['partial'] = True
        super(PatchModelSerializer, self).__init__(*args, **kwargs)


class SystemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SystemStatus
        fields = '__all__'

class OperatingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OperatingSystem
        fields = '__all__'

class SystemTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SystemType
        fields = '__all__'


class ServerModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ServerModel
        fields = '__all__'

class SystemSerializer(serializers.ModelSerializer):
    system_rack = SystemRackField(required=False)
    system_status = SystemStatusField()
    system_type = SystemTypeField()
    operating_system = OperatingSystemTypeField(required=False, allow_null=True)
    server_model = ServerModelTypeField(required=False)
    warranty_start = WarrantyStartField(required=False)
    warranty_end = WarrantyEndField(required=False)
    # server_model = serializers.StringRelatedField(many=False)

    def validate(self, data):

        if 'warranty_start' not in data or data['warranty_start'] == None:
            data['warranty_start'] = datetime.date.today()
            data['warranty_end'] = datetime.date.today() + relativedelta(
                years=+1)


        if 'serial' not in data or data['serial'] == '':
            if data['server_model'].model != u'VMware Virtual Platform':
                pass
                #raise serializers.ValidationError("Serial Required", code=400)

        if self.context['request'].method != 'PATCH':
            if System.objects.filter(hostname=data['hostname']):
                raise serializers.ValidationError(
                    "Hostname already used", code=400
                )
        return data

    class Meta:
        model = models.System
        fields = '__all__'

class SystemRackSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()
    systems = serializers.SerializerMethodField()
    site = SiteField()
    class Meta:
        model = models.SystemRack
        fields = '__all__'

    def get_systems(self, value):

        serializer = SystemSerializer(value.systems().order_by("-rack_order"), many=True)
        return serializer.data

    def get_location(self, value):
        try:
            return value.location.name
        except AttributeError:
            return ""

    def get_site_name(self, value):
        try:
            return value.site.name
        except AttributeError:
            return ""



class MultipleFieldLookupMixin(object):
    """
    Apply this mixin to any view or viewset to get multiple field filtering
    based on a `lookup_fields` attribute,
    instead of the default single field filtering.
    """

    def get_object(self):
        # queryset = self.filter_queryset(queryset)
        for field in self.lookup_fields:
            filter = {}
            try:
                    filter[field] = self.kwargs['pk']
                    return self.queryset.filter(**filter).first()
            except Exception:
                continue

        # return get_object_or_404(queryset, **filter)  # Lookup the object
        return []


class SystemTypeViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    queryset = models.SystemType.objects.all()
    serializer_class = SystemTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (SearchFilter,)
    lookup_fields = ('pk', 'type_name')
    search_fields = ('id', 'type_name')


class SystemRackViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):


    queryset = models.SystemRack.objects.all()
    serializer_class = SystemRackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (SearchFilter,)
    lookup_fields = ('pk', 'name')
    search_fields = ('id', 'name', 'location__name', 'site__name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid()
        if not serializer.is_valid():
            for error in serializer.errors:
                error_title = serializer.errors[error][0].title()
                error_resp = {'non_field_errors': [error_title]}
                raise serializers.ValidationError(error_resp)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

class ServerModelViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    queryset = models.ServerModel.objects.all()
    serializer_class = ServerModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (SearchFilter,)
    lookup_fields = ('pk', 'id', 'vendor', 'model')
    search_fields = ('id', 'vendor', 'model')

    def filter_queryset(self, queryset):
        queryset = super(ServerModelViewSet, self).filter_queryset(queryset)
        return queryset.order_by('id')

class SystemStatusViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    queryset = models.SystemStatus.objects.all()
    serializer_class = SystemStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (SearchFilter,)
    lookup_fields = ('pk', 'id', 'status')
    search_fields = ('id', 'status')



class OperatingSystemViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    queryset = models.OperatingSystem.objects.all()
    serializer_class = OperatingSystemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (SearchFilter,)
    lookup_fields = ('pk', 'name', 'version')
    search_fields = ('id', 'name', 'version')

class SystemViewSet(MultipleFieldLookupMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.System.objects.all()
    serializer_class = SystemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (DjangoFilterBackend,)
    lookup_fields = ('pk', 'id', 'hostname')
    filter_fields = ('id', 'hostname', 'system_status__status')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        if not serializer.is_valid():
            import pdb; pdb.set_trace()
            for error in serializer.errors:
                error_title = serializer.errors[error][0].title()
                error_resp = {'non_field_errors': [error_title]}
                raise serializers.ValidationError(error_resp)
        serializer.save(request=request)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_200_OK, headers=headers
        )

    def create(self, request, *args, **kwargs):
        # tmp = request.data.copy()
        # tmp['server_model'] = 5
        empty_or_zero_remove = [
            'operating_system',
            'rack_order',
            'system_rack',
            'system_type',
        ]

        for attr in empty_or_zero_remove:
            if request.data[attr] == 0 or request.data[attr] == '':
                del request.data[attr]

        serializer = self.get_serializer(data=request.data)
        error_title_required = 'This Field Is Required.'
        if not serializer.is_valid():
            for error in serializer.errors:
                error_title = serializer.errors[error][0].title()
                if error_title == error_title_required:
                    error_title = "{} ({})".format(error_title, error)
                error_resp = {'non_field_errors': [error_title]}
                raise serializers.ValidationError(error_resp)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
        except (AttributeError, Http404):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save()
