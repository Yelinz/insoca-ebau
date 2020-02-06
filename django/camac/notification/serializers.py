from collections import namedtuple
from datetime import date, timedelta
from html import escape
from logging import getLogger

import inflection
import jinja2
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_noop
from rest_framework import exceptions
from rest_framework_json_api import serializers

from camac.caluma.api import CalumaApi
from camac.constants import kt_bern as be_constants
from camac.core.models import (
    Activation,
    Answer,
    BillingV2Entry,
    Journal,
    JournalT,
    WorkflowEntry,
)
from camac.core.translations import get_translations
from camac.instance.mixins import InstanceEditableMixin
from camac.instance.models import Instance
from camac.instance.validators import transform_coordinates
from camac.user.models import Role, Service
from camac.utils import flatten

from ..core import models as core_models
from . import models

request_logger = getLogger("django.request")


class NoticeMergeSerializer(serializers.Serializer):
    service = serializers.StringRelatedField(source="activation.service")
    notice_type = serializers.StringRelatedField()
    content = serializers.CharField()


class ActivationMergeSerializer(serializers.Serializer):
    deadline_date = serializers.DateTimeField(format=settings.MERGE_DATE_FORMAT)
    start_date = serializers.DateTimeField(format=settings.MERGE_DATE_FORMAT)
    end_date = serializers.DateTimeField(format=settings.MERGE_DATE_FORMAT)
    circulation_state = serializers.StringRelatedField()
    service = serializers.StringRelatedField()
    reason = serializers.CharField()
    circulation_answer = serializers.StringRelatedField()
    notices = NoticeMergeSerializer(many=True)


class BillingEntryMergeSerializer(serializers.Serializer):
    amount = serializers.FloatField()
    service = serializers.StringRelatedField()
    created = serializers.DateTimeField(format=settings.MERGE_DATE_FORMAT)
    account = serializers.SerializerMethodField()
    account_number = serializers.SerializerMethodField()

    def get_account(self, billing_entry):
        billing_account = billing_entry.billing_account
        return "{0} / {1}".format(billing_account.department, billing_account.name)

    def get_account_number(self, billing_entry):
        return billing_entry.billing_account.account_number


class InstanceMergeSerializer(InstanceEditableMixin, serializers.Serializer):
    """Converts instance into a dict to be used with template merging."""

    # TODO: document.Template and notification.NotificationTemplate should
    # be moved to its own app template including this serializer.

    location = serializers.StringRelatedField()
    identifier = serializers.CharField()
    activations = ActivationMergeSerializer(many=True)
    billing_entries = BillingEntryMergeSerializer(many=True)
    answer_period_date = serializers.SerializerMethodField()
    publication_date = serializers.SerializerMethodField()
    instance_id = serializers.IntegerField()
    public_dossier_link = serializers.SerializerMethodField()
    internal_dossier_link = serializers.SerializerMethodField()
    registration_link = serializers.SerializerMethodField()
    leitbehoerde_name = serializers.SerializerMethodField()
    form_name = serializers.SerializerMethodField()
    ebau_number = serializers.SerializerMethodField()
    base_url = serializers.SerializerMethodField()
    rejection_feedback = serializers.SerializerMethodField()
    current_service = serializers.SerializerMethodField()
    date_dossiervollstandig = serializers.SerializerMethodField()
    date_dossiereingang = serializers.SerializerMethodField()
    date_start_zirkulation = serializers.SerializerMethodField()
    billing_total_kommunal = serializers.SerializerMethodField()
    billing_total_kanton = serializers.SerializerMethodField()
    billing_total = serializers.SerializerMethodField()

    # TODO: these is currently bern specific, as it depends on instance state
    # identifiers. This will likely need some client-specific switch logic
    # some time in the future
    total_activations = serializers.SerializerMethodField()
    completed_activations = serializers.SerializerMethodField()
    pending_activations = serializers.SerializerMethodField()
    activation_statement_de = serializers.SerializerMethodField()
    activation_statement_fr = serializers.SerializerMethodField()

    def __init__(self, instance, *args, activation=None, escape=False, **kwargs):
        self.escape = escape

        lookup = {"circulation__instance": instance}
        if activation:
            self.activation = activation
            self.circulation = self.activation.circulation

            lookup.update(
                {
                    "circulation": self.activation.circulation,
                    "service_parent": self.activation.service_parent,
                }
            )

        instance.activations = Activation.objects.filter(**lookup)

        super().__init__(instance, *args, **kwargs)

    def _escape(self, data):
        result = data
        if isinstance(data, str):
            result = escape(data)
        elif isinstance(data, list):
            result = [self._escape(value) for value in data]
        elif isinstance(data, dict):
            result = {key: self._escape(value) for key, value in data.items()}

        return result

    def get_rejection_feedback(self, instance):  # pragma: no cover
        feedback = Answer.objects.filter(
            instance=instance, chapter=20001, question=20037, item=1
        ).first()
        if feedback:
            return feedback.answer
        return ""

    def get_answer_period_date(self, instace):
        answer_period_date = date.today() + timedelta(days=settings.MERGE_ANSWER_PERIOD)
        return answer_period_date.strftime(settings.MERGE_DATE_FORMAT)

    def get_publication_date(self, instance):
        publication_entry = instance.publication_entries.first()

        return (
            publication_entry
            and publication_entry.publication_date.strftime(settings.MERGE_DATE_FORMAT)
            or ""
        )

    def get_leitbehoerde_name(self, instance):
        """Return current active service of the instance."""
        return instance.active_service or "-"

    def get_current_service(self, instance):
        """Return current service of the active user."""
        try:
            service = self.context["request"].group.service

            return service.get_name() if service else "-"
        except KeyError:
            return "-"

    def get_activation_statement_de(self, instance):
        return self._get_activation_statement(instance, "de")

    def get_activation_statement_fr(self, instance):
        return self._get_activation_statement(instance, "fr")

    def _get_activation_statement(self, instance, language):
        if not getattr(self, "circulation", None):
            return ""

        total = self.get_total_activations(instance)
        pending = self.get_pending_activations(instance)

        created = date.fromtimestamp(int(self.circulation.name)).strftime("%d.%m.%Y")

        circulation_name = {
            "de": f"Zirkulation vom {created}",
            "fr": f"la circulation du {created}",
        }

        if total == 0:  # pragma: no cover (this should never happen)
            return ""
        elif pending == 0:
            message = {
                "de": f"Alle {total} Stellungnahmen der {circulation_name.get('de')} sind nun eingegangen.",
                "fr": f"Tous les {total} prises de position de {circulation_name.get('fr')} ont été reçues.",
            }
        else:  # pending > 0:
            message = {
                "de": f"{pending} von {total} Stellungnahmen der {circulation_name.get('de')} stehen noch aus.",
                "fr": f"{pending} de {total} prises de position de {circulation_name.get('fr')} sont toujours en attente.",
            }

        return message.get(language)

    def get_form_name(self, instance):
        if settings.APPLICATION["FORM_BACKEND"] == "camac-ng":
            return instance.form.get_name()

        return CalumaApi().get_form_name(instance) or "-"

    def get_ebau_number(self, instance):
        if settings.APPLICATION["FORM_BACKEND"] != "caluma":
            return "-"

        return CalumaApi().get_ebau_number(instance) or "-"

    def get_internal_dossier_link(self, instance):
        return settings.INTERNAL_INSTANCE_URL_TEMPLATE.format(instance_id=instance.pk)

    def get_public_dossier_link(self, instance):
        return settings.PUBLIC_INSTANCE_URL_TEMPLATE.format(instance_id=instance.pk)

    def get_registration_link(self, instance):
        return settings.REGISTRATION_URL

    def get_base_url(self, instance):
        return settings.INTERNAL_BASE_URL

    def _get_workflow_entry_date(self, instance, item_id):
        entry = WorkflowEntry.objects.filter(
            instance=instance, workflow_item=item_id
        ).first()
        if entry:
            return entry.workflow_date.strftime(settings.MERGE_DATE_FORMAT)
        return "---"

    def get_date_dossiervollstandig(self, instance):
        return self._get_workflow_entry_date(
            instance,
            settings.APPLICATION.get("WORKFLOW_ITEMS", {}).get("INSTANCE_COMPLETE"),
        )

    def get_date_dossiereingang(self, instance):
        return self._get_workflow_entry_date(
            instance, settings.APPLICATION.get("WORKFLOW_ITEMS", {}).get("SUBMIT")
        )

    def get_date_start_zirkulation(self, instance):
        return self._get_workflow_entry_date(
            instance, settings.APPLICATION.get("WORKFLOW_ITEMS", {}).get("START_CIRC")
        )

    def get_billing_total_kommunal(self, instance):
        return BillingV2Entry.objects.filter(
            instance=instance, organization=BillingV2Entry.MUNICIPAL
        ).aggregate(total=Sum("final_rate"))["total"]

    def get_billing_total_kanton(self, instance):
        return BillingV2Entry.objects.filter(
            instance=instance, organization=BillingV2Entry.CANTONAL
        ).aggregate(total=Sum("final_rate"))["total"]

    def get_billing_total(self, instance):
        return BillingV2Entry.objects.filter(instance=instance).aggregate(
            total=Sum("final_rate")
        )["total"]

    def get_total_activations(self, instance):
        return instance.activations.count()

    def get_completed_activations(self, instance):
        return instance.activations.filter(
            circulation_state_id=be_constants.CIRCULATION_STATE_DONE
        ).count()

    def get_pending_activations(self, instance):
        return instance.activations.filter(
            circulation_state_id=be_constants.CIRCULATION_STATE_WORKING
        ).count()

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        for field in instance.fields.all():
            name = inflection.underscore("field-" + field.name)
            value = field.value

            if (
                field.name == settings.APPLICATION.get("COORDINATE_QUESTION", "")
                and value is not None
            ):
                value = "\n".join(transform_coordinates(value))
            elif field.name in settings.APPLICATION.get("QUESTIONS_WITH_OVERRIDE", []):
                override = instance.fields.filter(name=f"{field.name}-override").first()
                value = override.value if override else value

            ret[name] = value

        if self.escape:
            ret = self._escape(ret)

        return ret


class IssueMergeSerializer(serializers.Serializer):
    deadline_date = serializers.DateField()
    text = serializers.CharField()

    def to_representation(self, issue):
        ret = super().to_representation(issue)

        # include instance merge fields
        ret.update(InstanceMergeSerializer(issue.instance, context=self.context).data)

        return ret


class NotificationTemplateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["service"] = self.context["request"].group.service
        return super().create(validated_data)

    class Meta:
        model = models.NotificationTemplate
        fields = ("purpose", "subject", "body", "type")


class NotificationTemplateMergeSerializer(
    InstanceEditableMixin, serializers.Serializer
):
    instance_editable_permission = None
    """
    No specific permission needed to send notificaion
    """

    instance = serializers.ResourceRelatedField(queryset=Instance.objects.all())
    activation = serializers.ResourceRelatedField(
        queryset=Activation.objects.all(), required=False
    )
    notification_template = serializers.ResourceRelatedField(
        queryset=models.NotificationTemplate.objects.all()
    )
    subject = serializers.CharField(required=False)
    body = serializers.CharField(required=False)

    def _merge(self, value, instance, activation=None):
        try:
            value_template = jinja2.Template(value)
            data = InstanceMergeSerializer(
                instance, context=self.context, activation=activation
            ).data

            # some cantons use uppercase placeholders. be as compatible as possible
            data.update({k.upper(): v for k, v in data.items()})
            return value_template.render(data)
        except jinja2.TemplateError as e:
            raise exceptions.ValidationError(str(e))

    def validate(self, data):
        notification_template = data["notification_template"]
        instance = data["instance"]
        activation = data.get("activation")

        data["subject"] = self._merge(
            data.get("subject", notification_template.get_trans_attr("subject")),
            instance,
            activation=activation,
        )
        data["body"] = self._merge(
            data.get("body", notification_template.get_trans_attr("body")),
            instance,
            activation=activation,
        )
        data["pk"] = "{0}-{1}".format(notification_template.pk, instance.pk)

        return data

    def create(self, validated_data):
        NotificationTemplateMerge = namedtuple(
            "NotificationTemplateMerge", validated_data.keys()
        )
        obj = NotificationTemplateMerge(**validated_data)

        return obj

    class Meta:
        resource_name = "notification-template-merges"


class NotificationTemplateSendmailSerializer(NotificationTemplateMergeSerializer):
    recipient_types = serializers.MultipleChoiceField(
        choices=(
            "activation_deadline_today",
            "applicant",
            "municipality",
            "caluma_municipality",
            "service",
            "unnotified_service",
            "leitbehoerde",
            "construction_control",
            "email_list",
        )
    )
    email_list = serializers.CharField(required=False)

    def _get_recipients_caluma_municipality(self, instance):  # pragma: no cover
        municipality_service_id = CalumaApi().get_municipality(instance)

        if municipality_service_id:
            service = Service.objects.filter(pk=municipality_service_id).first()
            return [{"to": service.email}]

    def _get_recipients_applicant(self, instance):
        return [
            {"to": applicant.invitee.email}
            for applicant in instance.involved_applicants.all()
            if applicant.invitee
        ]

    def _get_recipients_activation_deadline_today(self, instance):
        """Return recipients of activations for an instance which  deadline expires exactly today."""
        activations = Activation.objects.filter(
            ~Q(circulation_state__name="DONE"),
            deadline_date__date=date.today(),
            circulation__instance__instance_state__name="circulation",
            circulation__instance=instance,
        )
        services = {a.service for a in activations}
        return flatten(
            [self._get_responsible(instance, service) for service in services]
        )

    def _get_responsible(self, instance, service):
        responsible_old = instance.responsible_services.filter(
            service=service
        ).values_list("responsible_user__email", flat=True)
        responsible_new = instance.responsibilities.filter(service=service).values_list(
            "user__email", flat=True
        )
        responsibles = responsible_new.union(responsible_old)

        try:
            return [{"to": responsibles[0], "cc": service.email}]
        except IndexError:
            return [{"to": service.email}]

    def _get_recipients_leitbehoerde(self, instance):  # pragma: no cover
        return self._get_responsible(instance, instance.active_service)

    def _get_recipients_municipality(self, instance):
        return self._get_responsible(instance, instance.group.service)

    def _get_recipients_unnotified_service(self, instance):
        activations = Activation.objects.filter(
            circulation__instance_id=instance.pk, email_sent=0
        )
        services = {a.service for a in activations}

        return flatten(
            [self._get_responsible(instance, service) for service in services]
        )

    def _get_recipients_service(self, instance):
        services = Service.objects.filter(
            pk__in=instance.circulations.values("activations__service")
        )

        return flatten(
            [self._get_responsible(instance, service) for service in services]
        )

    def _get_recipients_construction_control(self, instance):
        instance_services = core_models.InstanceService.objects.filter(
            instance=instance,
            service__service_group__name="construction-control",
            active=1,
        )
        return flatten(
            [
                self._get_responsible(instance, instance_service.service)
                for instance_service in instance_services
            ]
        )

    def _get_recipients_email_list(self, instance):
        return [{"to": to} for to in self.validated_data["email_list"].split(",")]

    def _recipient_log(self, recipient):
        return recipient["to"] + (
            f" (CC: {recipient['cc']})" if "cc" in recipient else ""
        )

    def create(self, validated_data):
        subj_prefix = settings.EMAIL_PREFIX_SUBJECT
        body_prefix = settings.EMAIL_PREFIX_BODY

        instance = validated_data["instance"]

        result = 0

        for recipient_type in sorted(validated_data["recipient_types"]):
            recipients = getattr(self, "_get_recipients_%s" % recipient_type)(instance)
            subject = subj_prefix + validated_data["subject"]
            body = body_prefix + validated_data["body"]

            valid_recipients = [r for r in recipients if r.get("to")]
            for recipient in valid_recipients:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    # EmailMessage needs "to" and "cc" to be lists
                    **{
                        k: [e.strip() for e in email.split(",")]
                        for (k, email) in recipient.items()
                        if email
                    },
                )

                result += email.send()

                request_logger.info(
                    f'Sent email "{subject}" to {self._recipient_log(recipient)}'
                )

            # If no request context was provided to the serializer we assume the
            # mail delivery is part of a batch job initalized by the system
            # operation user.

            if self.context:
                user = self.context["request"].user
            else:
                user = (
                    Role.objects.get(name="support")
                    .groups.order_by("group_id")
                    .first()
                    .users.first()
                )

            if (
                settings.APPLICATION_NAME == "kt_bern"
                or settings.APPLICATION_NAME == "demo"
            ):  # pragma: no cover
                journal_entry = Journal.objects.create(
                    instance=instance,
                    mode="auto",
                    additional_text=body,
                    created=timezone.now(),
                    user=user,
                )
                for (lang, text) in get_translations(
                    gettext_noop("Notification sent to %(receiver)s (%(subject)s)")
                ):
                    recipients_log = ", ".join(
                        [self._recipient_log(r) for r in recipients]
                    )
                    JournalT.objects.create(
                        journal=journal_entry,
                        text=text % {"receiver": recipients_log, "subject": subject},
                        additional_text=body,
                        language=lang,
                    )

        return result

    class Meta:
        resource_name = "notification-template-sendmails"


class PermissionlessNotificationTemplateSendmailSerializer(
    NotificationTemplateSendmailSerializer
):
    """
    Send emails without checking for instance permission.

    This serializer subclasses NotificationTemplateSendmailSerializer and
    overloads the validate_instance method of the InstanceEditableMixin to
    disable permission checking the instance and allow anyone to send a email.
    """

    # Temporary pragma no cover, remove when publication permission endpoint is reenabled
    # revert !2353 to remove
    def validate_instance(self, instance):  # pragma: no cover
        return instance
