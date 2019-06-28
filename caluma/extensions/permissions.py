import json
import os
from logging import getLogger

import requests
from django.core.exceptions import ObjectDoesNotExist

from caluma.core.mutation import Mutation
from caluma.core.permissions import (
    BasePermission,
    object_permission_for,
    permission_for,
)
from caluma.form.schema import RemoveAnswer, SaveDocument, SaveDocumentAnswer
from caluma.workflow.models import Case
from caluma.workflow.schema import SaveCase, StartCase

from .visibilities import group, role

log = getLogger()

"""Caluma permissions for Kanton Bern"""

INSTANCE_STATES = {
    "gesuchsteller": ["1", "10000"],  # Neu, Zurückgewiesen
    "_default": ["20007"],  # In Korrektur
}
INSTANCE_STATES_META = {
    "internal": ["20000"],  # eBau-Nummer zu vergeben
    "_default": [],
}


class CustomPermission(BasePermission):
    @object_permission_for(Mutation)
    def has_object_permission_default(self, mutation, info, instance):
        operation = mutation.__name__
        log.debug(
            f"ACL: fallback object permission: rejecting "
            f"mutation '{operation}' on {instance}"
        )
        return False

    @permission_for(Mutation)
    def has_permission_default(self, mutation, info):
        operation = mutation.__name__
        log.debug(f"fallback permission: rejecting mutation '{operation}'")
        return False

    # Case
    @permission_for(StartCase)
    def has_permission_for_start_case(self, mutation, info):
        return True

    @permission_for(SaveCase)
    def has_permission_for_save_case(self, mutation, info):
        return True

    @object_permission_for(SaveCase)
    def has_object_permission_for_save_case(self, mutation, info, instance):
        return self.has_camac_edit_permission(
            instance.document.pk, info, only_meta=True
        )

    # Document
    @permission_for(SaveDocument)
    def has_permission_for_savedocument(self, mutation, info):
        log.debug("ACL: SaveDocument permission")
        return True

    @object_permission_for(SaveDocument)
    def has_object_permission_for_savedocument(self, mutation, info, instance):
        log.debug("ACL: SaveDocument object permission")
        return self.has_camac_edit_permission(instance.family, info)

    # Answer
    @permission_for(SaveDocumentAnswer)
    def has_permission_for_savedocumentanswer(self, mutation, info):
        return True

    @object_permission_for(SaveDocumentAnswer)
    def has_object_permission_for_savedocumentanswer(self, mutation, info, instance):
        return self._can_change_answer(info, instance)

    @permission_for(RemoveAnswer)
    def has_permission_for_removeanswer(self, mutation, info):
        return True

    @object_permission_for(RemoveAnswer)
    def has_object_permission_for_removeanswer(self, mutation, info, instance):
        return self._can_change_answer(info, instance)

    def _can_change_answer(self, info, instance):
        return self.has_camac_edit_permission(instance.document.family, info)

    def has_camac_edit_permission(self, document_family, info, only_meta=False):
        # find corresponding case
        try:
            case = Case.objects.get(document_id=document_family)
        except ObjectDoesNotExist:
            # if the document is unlinked, allow changing it
            # this is used for new table rows
            return True

        camac_api = os.environ.get("CAMAC_NG_URL", "http://camac-ng.local").strip("/")
        instance_id = case.meta.get("camac-instance-id", None)
        if instance_id is None and only_meta:
            # this is a fresh case that needs to be extended with metadata
            # for the permission to work. so for now, allow full access
            return True

        resp = requests.get(
            f"{camac_api}/api/v1/instances/{instance_id}?include=instance-state",
            # forward role as filter
            {"role": role(info), "group": group(info)},
            # Forward authorization header
            headers={"Authorization": info.context.META.get("HTTP_AUTHORIZATION")},
        )

        if resp.status_code != requests.codes.ok:
            log.info(f"ACL: Got {resp.status_code} from NG API -> no access")
            return False

        try:
            jsondata = resp.json()
            if "error" in jsondata:
                # forward Instance API error to client
                raise RuntimeError("Error from NG API: %s" % jsondata["error"])
            instance_state_id = jsondata["data"]["relationships"]["instance-state"][
                "data"
            ]["id"]
            log.debug(f"ACL: Camac NG instance state: {instance_state_id}")
            return instance_state_id in INSTANCE_STATES.get(
                role(info), INSTANCE_STATES["_default"]
            ) or (
                only_meta
                and instance_state_id
                in INSTANCE_STATES_META.get(
                    role(info), INSTANCE_STATES_META["_default"]
                )
            )

        except json.decoder.JSONDecodeError:
            raise RuntimeError("NG API returned non-JSON response, check configuration")

        except KeyError:
            raise RuntimeError(
                f"NG API returned unexpected data structure (no data key) {jsondata}"
            )
