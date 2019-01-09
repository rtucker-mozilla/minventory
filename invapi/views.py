from systems import models
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from rest_framework import serializers


class SystemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SystemStatus
        fields = '__all__'
class SystemSerializer(serializers.ModelSerializer):
    system_status = serializers.StringRelatedField(many=False)
    class Meta:
        model = models.System
        fields = '__all__'


class SystemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = models.System.objects.all().order_by('-id')
    serializer_class = SystemSerializer
    permission_classes = (IsAuthenticated,)

