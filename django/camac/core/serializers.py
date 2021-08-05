from caluma.caluma_workflow import api as workflow_api, models as workflow_models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import exceptions
from rest_framework.validators import UniqueTogetherValidator
from rest_framework_json_api import relations, serializers

from camac.instance.models import Instance
from camac.notification import (
    serializers as notification_serializers,
    utils as notification_utils,
)
from camac.user.models import User

from . import models


class MultilingualField(serializers.Field):
    """
    Custom field for our legacy multilingual model fields.

    Make sure you pop the value from `validated_data` and handle any modifications to
    the translation table.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, value):
        return value.get_trans_attr(self.source or self.field_name)

    def to_internal_value(self, data):
        return data


class MultilingualSerializer(serializers.Serializer):
    name = MultilingualField()


class PublicationEntrySerializer(serializers.ModelSerializer):
    instance = relations.ResourceRelatedField(queryset=Instance.objects)
    description = serializers.SerializerMethodField()

    def get_description(self, obj):
        # We include this form field to avoid creating a whitelist for fields
        try:
            return obj.instance.fields.get(name="bezeichnung").value
        except ObjectDoesNotExist:
            return ""

    included_serializers = {"instance": "camac.instance.serializers.InstanceSerializer"}

    @transaction.atomic
    def update(self, instance, validated_data):
        if not instance.is_published and validated_data["is_published"]:

            models.WorkflowEntry.objects.create(
                group=instance.instance.group.pk,
                workflow_item_id=settings.APPLICATION.get("WORKFLOW_ITEMS", {}).get(
                    "PUBLICATION"
                ),
                instance_id=instance.instance.pk,
                # remove the microseconds because this date is displayed in camac and
                # camac can't handle microseconds..
                workflow_date=instance.publication_date.replace(microsecond=0),
            )

            work_item = self.instance.instance.case.work_items.filter(
                task_id="publication", status=workflow_models.WorkItem.STATUS_READY
            ).first()

            # TODO: test this
            if work_item:  # pragma: no cover
                workflow_api.complete_work_item(
                    work_item=work_item,
                    user=self.context["request"].caluma_info.context.user,
                )

        return super().update(instance, validated_data)

    class Meta:
        model = models.PublicationEntry
        fields = ("instance", "publication_date", "is_published", "description")
        read_only_fields = ("description",)


class PublicationEntryUserPermissionSerializer(serializers.ModelSerializer):
    publication_entry = relations.ResourceRelatedField(
        queryset=models.PublicationEntry.objects
    )
    user = relations.ResourceRelatedField(
        queryset=User.objects, default=serializers.CurrentUserDefault()
    )
    status = serializers.ChoiceField(
        choices=models.PublicationEntryUserPermission.STATES
    )

    included_serializers = {"user": "camac.user.serializers.UserSerializer"}

    @transaction.atomic
    def create(self, validated_data):
        validated_data["status"] = models.PublicationEntryUserPermission.PENDING
        permission = super().create(validated_data)

        # send notification email when configured
        notification_template = settings.APPLICATION["NOTIFICATIONS"].get(
            "PUBLICATION_PERMISSION"
        )

        if notification_template:
            notification_utils.send_mail(
                notification_template,
                self.context,
                notification_serializers.PermissionlessNotificationTemplateSendmailSerializer,
                recipient_types=["municipality"],
                instance={
                    "id": validated_data["publication_entry"].instance.pk,
                    "type": "instances",
                },
            )

        return permission

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data["status"] == models.PublicationEntryUserPermission.PENDING:
            raise exceptions.ValidationError("Invalid State")

        return super().update(instance, validated_data)

    class Meta:
        model = models.PublicationEntryUserPermission
        fields = ("status", "publication_entry", "user")
        read_only_fields = ("publication_entry", "user")
        validators = [
            UniqueTogetherValidator(
                queryset=models.PublicationEntryUserPermission.objects.all(),
                fields=["publication_entry", "user"],
            )
        ]


class AuthoritySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Authority
        fields = ("authority_id", "name")


class WorkflowEntrySerializer(serializers.ModelSerializer):
    workflow_item = relations.ResourceRelatedField(queryset=models.WorkflowItem.objects)

    class Meta:
        model = models.WorkflowEntry
        fields = (
            "workflow_entry_id",
            "workflow_date",
            "instance",
            "workflow_item",
            "group",
        )
