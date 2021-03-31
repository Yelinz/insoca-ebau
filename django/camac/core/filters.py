from django_filters.rest_framework import FilterSet

from camac.filters import NumberFilter

from . import models


class PublicationEntryFilterSet(FilterSet):
    class Meta:
        model = models.PublicationEntry
        fields = ("instance",)


class PublicationEntryUserPermissionFilterSet(FilterSet):
    class Meta:
        model = models.PublicationEntryUserPermission
        fields = ("publication_entry", "user", "status")


class WorkflowEntryFilterSet(FilterSet):
    instance = NumberFilter(field_name="instance_id")
    workflow_item_id = NumberFilter(field_name="workflow_item_id")

    class Meta:
        model = models.WorkflowEntry
        fields = ("workflow_item_id", "instance")
