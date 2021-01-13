import mimetypes
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext as _
from django_clamd.validators import validate_file_infection
from manabi.token import Key, Token
from manabi.util import from_string
from rest_framework import exceptions
from rest_framework_json_api import serializers

from camac.core import serializers as core_serializers
from camac.instance.mixins import InstanceEditableMixin
from camac.notification.serializers import NotificationTemplateSendmailSerializer
from camac.relations import FormDataResourceRelatedField
from camac.user.relations import (
    CurrentUserFormDataResourceRelatedField,
    GroupFormDataResourceRelatedField,
    ServiceFormDataResourceRelatedField,
    ServiceResourceRelatedField,
)
from camac.user.serializers import CurrentGroupDefault, CurrentServiceDefault

from . import models, permissions


class AttachmentSectionSerializer(
    core_serializers.MultilingualSerializer, serializers.ModelSerializer
):
    mode = serializers.SerializerMethodField()
    description = core_serializers.MultilingualField()

    def get_mode(self, instance):
        request = self.context["request"]
        return instance.get_mode(request.group)

    class Meta:
        model = models.AttachmentSection
        meta_fields = ("mode",)
        fields = ("name", "description")


class AttachmentSerializer(InstanceEditableMixin, serializers.ModelSerializer):
    serializer_related_field = FormDataResourceRelatedField

    user = CurrentUserFormDataResourceRelatedField()
    group = GroupFormDataResourceRelatedField(default=CurrentGroupDefault())
    service = ServiceResourceRelatedField(default=CurrentServiceDefault())
    attachment_sections = FormDataResourceRelatedField(
        queryset=models.AttachmentSection.objects, many=True
    )
    webdav_link = serializers.SerializerMethodField()
    included_serializers = {
        "user": "camac.user.serializers.UserSerializer",
        "instance": "camac.instance.serializers.InstanceSerializer",
        "attachment_sections": AttachmentSectionSerializer,
        "service": "camac.user.serializers.ServiceSerializer",
    }

    def get_webdav_link(self, instance):
        if not settings.MANABI_ENABLE:  # pragma: no cover
            return None
        path = Path(instance.path.name)
        if path.suffix not in (".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"):
            return None
        view = self.context.get("view")
        if not view.has_write_permission(instance):
            return None
        key = Key(from_string(settings.MANABI_SHARED_KEY))
        token = Token(key, path)
        return f"ms-word:ofe|u|{settings.INTERNAL_BASE_URL}/dav/{token.as_url()}"

    def _get_default_attachment_sections(self, group):
        return models.AttachmentSection.objects.filter_group(group)[:1]

    def validate_attachment_sections(self, attachment_sections):
        group = self.context["request"].group

        if not attachment_sections:
            attachment_sections = self._get_default_attachment_sections(group)

        existing_section_ids = set()
        if self.instance:
            existing_section_ids = set(
                s.attachment_section_id for s in self.instance.attachment_sections.all()
            )

        for attachment_section in attachment_sections:
            if attachment_section.attachment_section_id in existing_section_ids:
                # document already assigned, so even if it's forbidden,
                # it's not a violation
                continue
            mode = attachment_section.get_mode(group)
            if mode not in [
                models.WRITE_PERMISSION,
                models.ADMIN_PERMISSION,
                models.ADMININTERNAL_PERMISSION,
                models.ADMINSERVICE_PERMISSION,
            ]:
                raise exceptions.ValidationError(
                    _(
                        "Not sufficent permissions to add file to "
                        "section %(section)s."
                    )
                    % {"section": attachment_section.name}
                )

        return attachment_sections

    def _validate_path_allowed_mime_types(self, path, attachment_sections):
        for section in attachment_sections:
            # empty allowed_mime_types -> any mime type allowed
            if (
                not section.allowed_mime_types
                or path.content_type in section.allowed_mime_types
            ):
                continue

            raise exceptions.ParseError(
                _(
                    "Invalid mime type for attachment. "
                    "Allowed types for section %(section_name)s are: %(allowed_mime_types)s"
                )
                % {
                    "section_name": section.get_trans_attr("name"),
                    "allowed_mime_types": ", ".join(
                        [
                            mime_type.split("/")[1]
                            for mime_type in section.allowed_mime_types
                        ]
                    ),
                }
            )
        validate_file_infection(path)
        return path

    def validate(self, data):
        custom_validate = permissions.VALIDATE_ATTACHMENTS.get(
            settings.APPLICATION_NAME, lambda _, data: data
        )
        data = custom_validate(self, data)

        if "path" in data:
            path = data["path"]

            attachment_sections = (
                data["attachment_sections"]
                if "attachment_sections" in data
                else self._get_default_attachment_sections(
                    self.context["request"].group
                )
            )

            self._validate_path_allowed_mime_types(path, attachment_sections)

            data["size"] = path.size
            data["mime_type"] = path.content_type
            data["name"] = path.name
        return data

    def create(self, validated_data):
        attachment = super().create(validated_data)
        attachment_sections = attachment.attachment_sections.all()

        for attachment_section in attachment_sections:
            if (
                attachment_section.notification_template_id
                and attachment_section.recipient_types
            ):
                # send mail when configured
                data = {
                    "instance": {"type": "instances", "id": attachment.instance_id},
                    "notification_template": {
                        "type": "notification-templates",
                        "id": attachment_section.notification_template_id,
                    },
                    "recipient_types": attachment_section.recipient_types,
                }
                serializer = NotificationTemplateSendmailSerializer(
                    data=data, context=self.context
                )
                serializer.is_valid() and serializer.save()

        return attachment

    def update(self, instance, validated_data):
        if (
            not (
                instance.instance.instance_state.name == "new"
                and instance.instance.previous_instance_state.name == "new"
            )
            and "path" in validated_data
        ):
            raise exceptions.ValidationError(_("Path may not be changed."))
        return super().update(instance, validated_data)

    class Meta:
        model = models.Attachment
        fields = (
            "attachment_sections",
            "date",
            "digital_signature",
            "instance",
            "is_confidential",
            "is_parcel_picture",
            "mime_type",
            "name",
            "path",
            "size",
            "user",
            "group",
            "service",
            "question",
            "context",
            "uuid",
            "webdav_link",
            "identifier",
        )
        read_only_fields = (
            "date",
            "mime_type",
            "name",
            "size",
            "user",
            "uuid",
            "webdav_link",
            "identifier",
        )


class TemplateSerializer(serializers.ModelSerializer):
    group = GroupFormDataResourceRelatedField(default=CurrentGroupDefault())
    service = ServiceFormDataResourceRelatedField(default=CurrentServiceDefault())

    def validate_path(self, path):
        if path.content_type != mimetypes.types_map[".docx"]:
            raise exceptions.ParseError(
                _("Invalid mime type for template. Allowed types are: docx")
            )

        validate_file_infection(path)

        return path

    class Meta:
        model = models.Template
        fields = ("name", "path", "group", "service")


class AttachmentDownloadHistorySerializer(serializers.ModelSerializer):
    group = GroupFormDataResourceRelatedField(default=CurrentGroupDefault())
    attachment = FormDataResourceRelatedField(queryset=models.Attachment.objects)

    class Meta:
        model = models.AttachmentDownloadHistory
        fields = ("date_time", "keycloak_id", "name", "attachment", "group")
