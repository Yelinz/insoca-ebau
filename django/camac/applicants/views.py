from django.conf import settings
from rest_framework import viewsets

from camac.instance.mixins import InstanceQuerysetMixin
from camac.notification.serializers import NotificationTemplateSendmailSerializer
from camac.user.permissions import permission_aware

from . import filters, models, serializers


class ApplicantsView(viewsets.ModelViewSet, InstanceQuerysetMixin):
    swagger_schema = None
    filterset_class = filters.ApplicantFilterSet
    serializer_class = serializers.ApplicantSerializer
    queryset = models.Applicant.objects.all().select_related(
        "invitee", "instance", "instance__instance_state"
    )
    prefetch_for_included = {"invitee": ["service"], "user": ["service"]}

    def create(self, request):
        created = super().create(request)

        # send notification email when configured
        notification_template = settings.APPLICATION["NOTIFICATIONS"]["APPLICANT"].get(
            "EXISTING" if created.data["invitee"] else "NEW"
        )
        if notification_template:
            context = self.get_serializer_context()
            sendmail_data = {
                "recipient_types": ["email_list"],
                "email_list": created.data["email"],
                "notification_template": {
                    "type": "notification-templates",
                    "id": notification_template,
                },
                "instance": {"id": created.data["instance"]["id"], "type": "instances"},
            }
            sendmail_serializer = NotificationTemplateSendmailSerializer(
                data=sendmail_data, context=context
            )
            sendmail_serializer.is_valid(raise_exception=True)
            sendmail_serializer.save()

        return created

    @permission_aware
    def has_create_permission(self):
        return True

    def has_create_permission_for_municipality(self):
        return False

    def has_create_permission_for_service(self):
        return False

    def has_create_permission_for_canton(self):
        return False

    def has_object_update_permission(self, obj):
        return False

    @permission_aware
    def has_object_destroy_permission(self, obj):
        # it should not be possible to delete the last involved applicant to
        # prevent having an instance without a user having access to it
        return obj.instance.involved_applicants.count() > 1

    def has_object_destroy_permission_for_municipality(self, obj):
        return False

    def has_object_destroy_permission_for_service(self, obj):
        return False

    def has_object_destroy_permission_for_canton(self, obj):
        return False
