import json
from logging import getLogger

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.authentication import get_authorization_header
from rest_framework.serializers import ValidationError
from rest_framework_json_api import serializers

from camac.constants import kt_bern as constants
from camac.notification.serializers import NotificationTemplateSendmailSerializer

from .. import models
from ...core import models as core_models
from .common import InstanceSerializer

request_logger = getLogger("django.request")


class BernInstanceSerializer(InstanceSerializer):

    instance_state = serializers.ResourceRelatedField(
        queryset=models.InstanceState.objects.all(),
        default=lambda: models.InstanceState.objects.order_by(
            "instance_state_id"
        ).first(),
    )
    previous_instance_state = serializers.ResourceRelatedField(
        queryset=models.InstanceState.objects.all(),
        default=lambda: models.InstanceState.objects.order_by(
            "instance_state_id"
        ).first(),
    )

    caluma_case_id = serializers.CharField(required=False)

    public_status = serializers.SerializerMethodField()

    def get_public_status(self, instance):
        STATUS_MAP = {
            constants.INSTANCE_STATE_NEW: constants.PUBLIC_INSTANCE_STATE_CREATING,
            constants.INSTANCE_STATE_EBAU_NUMMER_VERGEBEN: constants.PUBLIC_INSTANCE_STATE_RECEIVING,
            constants.INSTANCE_STATE_FORMELLE_PRUEFUNG: constants.PUBLIC_INSTANCE_STATE_COMMUNAL,
            constants.INSTANCE_STATE_MATERIELLE_PRUEFUNG: constants.PUBLIC_INSTANCE_STATE_COMMUNAL,
            constants.INSTANCE_STATE_DOSSIERPRUEFUNG: constants.PUBLIC_INSTANCE_STATE_COMMUNAL,
            constants.INSTANCE_STATE_KOORDINATION: constants.PUBLIC_INSTANCE_STATE_INIT_PROGRAM,
            constants.INSTANCE_STATE_VERFAHRENSPROGRAMM_INIT: constants.PUBLIC_INSTANCE_STATE_INIT_PROGRAM,
            constants.INSTANCE_STATE_ZIRKULATION: constants.PUBLIC_INSTANCE_STATE_INIT_PROGRAM,
            constants.INSTANCE_STATE_REJECTED: constants.PUBLIC_INSTANCE_STATE_REJECTED,
            constants.INSTANCE_STATE_CORRECTED: constants.PUBLIC_INSTANCE_STATE_CORRECTED,
            constants.INSTANCE_STATE_SELBSTDEKLARATION_AUSSTEHEND: constants.PUBLIC_INSTANCE_STATE_SELBSTDEKLARATION,
            constants.INSTANCE_STATE_SELBSTDEKLARATION_FREIGABEQUITTUNG: constants.PUBLIC_INSTANCE_STATE_SELBSTDEKLARATION,
            constants.INSTANCE_STATE_ABSCHLUSS_AUSSTEHEND: constants.PUBLIC_INSTANCE_STATE_ABSCHLUSS,
            constants.INSTANCE_STATE_ABSCHLUSS_DOKUMENTE: constants.PUBLIC_INSTANCE_STATE_ABSCHLUSS,
            constants.INSTANCE_STATE_ABSCHLUSS_FREIGABEQUITTUNG: constants.PUBLIC_INSTANCE_STATE_ABSCHLUSS,
            constants.INSTANCE_STATE_TO_BE_FINISHED: constants.PUBLIC_INSTANCE_STATE_FINISHED,
            constants.INSTANCE_STATE_FINISHED: constants.PUBLIC_INSTANCE_STATE_FINISHED,
        }
        return STATUS_MAP[instance.instance_state_id]

    def validate_instance_state(self, value):
        if not self.instance:  # pragma: no cover
            request_logger.info("Creating new instance, overriding %s" % value)
            return models.InstanceState.objects.get(trans__name="Neu")
        return value

    def _is_submit(self, data):
        if self.instance:
            old_version = models.Instance.objects.get(pk=self.instance.pk)
            return (
                old_version.instance_state_id != data.get("instance_state").pk
                and old_version.instance_state.get_name() in ["Neu", "Zurückgewiesen"]
                and data.get("instance_state").get_name() == "eBau-Nummer zu vergeben"
            )

    def validate(self, data):
        request_logger.info(f"validating instance {data.keys()}")
        case_id = data.get("caluma_case_id")

        # Fetch case data and meta information. Validate that the case doesn't
        # have another instance assigned already, and at the same time store
        # the data we need to update the case later on.
        request_logger.info("Fetching Caluma case info to validate instance creation")
        caluma_resp = requests.post(
            settings.CALUMA_URL,
            json={
                "query": """
                    query ($case_id: ID!) {
                      node(id:$case_id) {
                        ... on Case {
                          id
                          meta
                          workflow {
                            id
                          }
                          document {
                            id
                            form {
                              slug
                            }
                            answers(questions: ["gemeinde", "3-grundstueck"]) {
                              edges {
                                node {
                                  id
                                  question {
                                    slug
                                  }
                                  ... on StringAnswer {
                                    stringValue: value
                                  }
                                  ...on FormAnswer {
                                    formValue: value {
                                      id
                                      answers(question: "allgemeine-angaben") {
                                        edges {
                                          node {
                                            id
                                            ...on FormAnswer {
                                              formValue: value {
                                                id
                                                answers(question: "gemeinde") {
                                                  edges {
                                                    node {
                                                      id
                                                      ... on StringAnswer {
                                                        stringValue: value
                                                      }
                                                      question {
                                                        slug
                                                      }
                                                    }
                                                  }
                                                }
                                              }
                                            }
                                          }
                                        }
                                      }
                                    }
                                  }
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                """,
                "variables": {"case_id": case_id},
            },
            headers={
                "Authorization": get_authorization_header(self.context["request"])
            },
        )
        data["caluma_case_data"] = caluma_resp.json()["data"]["node"]
        request_logger.info("Caluma case information: %s", data["caluma_case_data"])

        if not self._is_submit(data):
            case_meta = data["caluma_case_data"]["meta"]
            if "camac-instance-id" in case_meta:  # pragma: no cover
                # Already linked. this should not be, as we just
                # created a new Camac instance for a caluma case that
                # has already an instance assigned
                raise ValidationError(
                    f"Caluma case already has an instance id "
                    f"assigned: {case_meta['camac-instance-id']}"
                )
        else:
            # TODO ask caluma if case is actually valid
            pass

        return data

    def create(self, validated_data):  # pragma: no cover
        case_id = validated_data.pop("caluma_case_id")
        case_data = validated_data.pop("caluma_case_data")
        case_meta = case_data["meta"]

        created = super().create(validated_data)

        created.involved_applicants.create(
            user=self.context["request"].user,
            invitee=self.context["request"].user,
            created=timezone.now(),
        )

        # Now, add instance id to case
        case_meta["camac-instance-id"] = created.pk

        caluma_resp = requests.post(
            settings.CALUMA_URL,
            json={
                "query": """
                       mutation save_instance_id ($input: SaveCaseInput!) {
                         saveCase (input: $input) {
                           case {
                             id
                             meta
                           }
                         }
                       }
                """,
                "variables": {
                    "input": {
                        "id": case_id,
                        "meta": json.dumps(case_meta),
                        "workflow": case_data["workflow"]["id"],
                    }
                },
            },
            headers={
                "Authorization": get_authorization_header(self.context["request"])
            },
        )
        if caluma_resp.status_code not in (200, 201):  # pragma: no cover
            raise ValidationError("Error while linking case and instance")

        return created

    @transaction.atomic
    def update(self, instance, validated_data):
        request_logger.info("Updating instance %s" % instance.pk)

        if not self._is_submit(validated_data):
            raise ValidationError(f"Updating cases is only allowed for submitting")

        validated_data["modification_date"] = timezone.now()

        if instance.instance_state.get_name() == "Zurückgewiesen":
            self.instance.instance_state = instance.previous_instance_state
        else:
            self.instance.instance_state = models.InstanceState.objects.get(
                trans__name="eBau-Nummer zu vergeben"
            )
        form = validated_data.get("caluma_case_data")["document"]["form"]["slug"]
        first_answer = validated_data.get("caluma_case_data")["document"]["answers"][
            "edges"
        ][0]["node"]

        service_id = None
        try:
            if form == "vorabklaerung-einfach":
                service_id = int(first_answer["stringValue"])
            else:  # pragma: no cover
                service_id = first_answer["formValue"]["answers"]["edges"][0]["node"][
                    "formValue"
                ]["answers"]["edges"][0]["node"]["stringValue"]
        except (KeyError, IndexError):  # pragma: no cover
            pass

        if not service_id:  # pragma: no cover
            request_logger.error("!!!Municipality not found!!!")
            service_id = 2  # default to Burgdorf

        core_models.InstanceService.objects.get_or_create(
            instance=self.instance,
            service_id=service_id,
            active=1,
            defaults={"activation_date": None},
        )

        self.instance.save()

        # send out emails upon submission
        for notification_config in settings.APPLICATION["NOTIFICATIONS"]["SUBMIT"]:
            self.notify_submit(**notification_config)

        return instance

    def notify_submit(self, template_id, recipient_types):
        """Send notification email."""

        # fake jsonapi request for notification serializer
        mail_data = {
            "instance": {"type": "instances", "id": self.instance.pk},
            "notification_template": {
                "type": "notification-templates",
                "id": template_id,
            },
            "recipient_types": recipient_types,
        }

        mail_serializer = NotificationTemplateSendmailSerializer(
            self.instance, mail_data
        )

        if not mail_serializer.is_valid():  # pragma: no cover
            errors = "; ".join(
                [f"{field}: {msg}" for field, msg in mail_serializer.errors.items()]
            )
            message = f"Cannot send email: {errors}"
            request_logger.error(message)
            raise ValidationError(message)

        mail_serializer.create(mail_serializer.validated_data)

    class Meta(InstanceSerializer.Meta):
        fields = InstanceSerializer.Meta.fields + ("caluma_case_id", "public_status")
        read_only_fields = InstanceSerializer.Meta.read_only_fields + ("public_status",)
