from dataclasses import fields
from typing import Optional

from camac.dossier_import.dossier_classes import Dossier
from camac.dossier_import.importers import DossierImporter
from camac.instance.models import Instance
from camac.instance.serializers import SUBMIT_DATE_FORMAT


class RenderError:
    pass


class FieldWriter:
    target: str
    value = None

    def __init__(
        self,
        target: str,
        owner=None,
        column_mapping: Optional[dict] = None,
        renderer: Optional[str] = None,
    ):
        self.target = target
        self.column_mapping = column_mapping
        self.renderer = renderer
        self.owner = owner

    def write(self, instance: Instance, value):
        raise NotImplementedError  # pragma: no cover

    def render(self, value):
        if self.renderer:
            try:
                renderer = getattr(self, f"render_{self.renderer}")
            except AttributeError:  # pragma: no cover
                raise NotImplementedError(
                    f"Renderer {self.renderer} is not configured for {self.__name__}"
                )
            return renderer(value)
        return value

    def render_datetime(self, value):
        try:
            return value.strftime(SUBMIT_DATE_FORMAT)
        except AttributeError:  # pragma: no cover
            raise RenderError(
                f"Failed to render {value} on {self} to a datetime to target {self.target}"
            )


class CamacNgAnswerFieldWriter(FieldWriter):
    def write(self, instance, value):
        (form_field, created,) = instance.fields.get_or_create(
            name=self.target, defaults=dict(value=self.render(value))
        )
        if not created:  # pragma: no cover
            form_field.value = self.render(value)
            form_field.save()


class CamacNgListAnswerWriter(FieldWriter):
    column_mapping = None

    def write(self, instance, value):
        mapped_values = [
            {
                column_name: getattr(row, key, None)
                for key, column_name in self.column_mapping.items()
            }
            for row in value
        ]
        field, created = instance.fields.get_or_create(
            name=self.target, defaults=dict(value=mapped_values)
        )
        if not created:  # pragma: no cover
            field.value = mapped_values
            field.save()


class WorkflowEntryFieldWriter(FieldWriter):
    target: int

    def write(self, instance, value):
        # entry = instance.workflowentry_set.filter(workflow_item_id=self.target).first()
        # if entry:
        #    entry.workflow_date = value
        #    entry.save()
        raise NotImplementedError  # pragma: no cover


class DossierWriter:
    def __init__(self, importer: DossierImporter):
        self.importer = importer

    def create_instance(self, dossier: Dossier):
        """Instance etc erstellen."""
        raise NotImplementedError  # pragma: no cover

    def write_fields(self, instance: Instance, dossier: Dossier):
        for field in fields(dossier):
            value = getattr(dossier, field.name, None)
            if not value:
                continue
            writer = getattr(self, field.name, None)
            if writer:
                writer.write(instance, getattr(dossier, field.name))

    def import_dossier(self, dossier: Dossier):
        # instance = self.create_instance(dossier)
        # self.write_fields(instance, dossier)
        # self._handle_dossier_attachments(dossier)
        # self._set_workflow_state(instance, dossier.Meta.target_state)
        raise NotImplementedError  # pragma: no cover

    def _set_workflow_state(self, instance: Instance, target_state: str):
        """Fast-Forward case to Dossier.Meta.target_state."""
        raise NotImplementedError  # pragma: no cover

    def _create_dossier_attachments(self, dossier: Dossier, instance: Instance):
        """Add attachment per dossier to the correct attachemnt section."""
        raise NotImplementedError  # pragma: no cover

    def _ensure_retrieveable(self):
        """Make imported dossiers identifiable.

        E. g. client deployment specific location for storing `internal id`
        """
        raise NotImplementedError  # pragma: no cover
