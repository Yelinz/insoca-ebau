from django.http import HttpResponse
from django_downloadview.api import ObjectDownloadView
from rest_framework import exceptions, parsers, viewsets
from rest_framework.decorators import detail_route
from rest_framework.views import APIView
from rest_framework_json_api import views
from sorl.thumbnail import delete, get_thumbnail

from camac.instance.mixins import InstanceQuerysetMixin
from camac.user.permissions import permission_aware

from . import models, serializers


class AttachmentView(InstanceQuerysetMixin, views.ModelViewSet):
    queryset = models.Attachment.objects.all()
    serializer_class = serializers.AttachmentSerializer
    # TODO: filter for instance, attachment_section, user
    parser_classes = (
        parsers.MultiPartParser,
        parsers.FormParser,
    )

    def get_base_queryset(self):
        return models.Attachment.objects.for_group(self.request.group)

    @permission_aware
    def get_queryset(self):
        return models.Attachment.objects.none()

    def update(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed('update')

    def has_object_destroy_permission(self, obj):
        mode = obj.attachment_section.get_mode(self.request.group)
        return mode == models.ADMIN_PERMISSION

    def perform_destroy(self, instance):
        """Delete image cache before deleting attachment."""
        delete(instance.path)
        super().perform_destroy(instance)

    @detail_route(methods=['get'])
    def thumbnail(self, request, pk=None):
        attachment = self.get_object()
        path = attachment.path
        try:
            thumbnail = get_thumbnail(path, geometry_string='x300')
        # no proper exception handling in solr thumbnail when image type is
        # invalid - workaround catching AtttributeError
        except AttributeError:
            raise exceptions.NotFound()
        return HttpResponse(thumbnail.read(), 'image/jpeg')


class AttachmentPathView(InstanceQuerysetMixin, ObjectDownloadView, APIView):
    """Attachment view to download attachment."""

    file_field = 'path'
    mime_type_field = 'mime_type'
    slug_field = 'path'
    slug_url_kwarg = 'path'
    basename_field = 'name'

    def get_base_queryset(self):
        return models.Attachment.objects.for_group(self.request.group)

    @permission_aware
    def get_queryset(self):
        return models.Attachment.objects.none()


class AttachmentSectionView(viewsets.ReadOnlyModelViewSet):
    ordering = ('sort', 'name')
    serializer_class = serializers.AttachmentSectionSerializer

    def get_queryset(self):
        return models.AttachmentSection.objects.for_group(self.request.group)
