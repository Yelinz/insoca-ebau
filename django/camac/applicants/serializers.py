from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework_json_api import relations, serializers

from camac.instance.mixins import InstanceEditableMixin
from camac.instance.models import Instance
from camac.user.relations import CurrentUserResourceRelatedField
from camac.user.serializers import UserSerializer

from . import models


class ApplicantSerializer(serializers.ModelSerializer, InstanceEditableMixin):
    user = CurrentUserResourceRelatedField()
    instance = relations.ResourceRelatedField(queryset=Instance.objects.all())
    invitee = relations.ResourceRelatedField(read_only=True)
    email = serializers.EmailField(required=True)

    included_serializers = {"invitee": UserSerializer, "user": UserSerializer}

    def validate(self, data):
        try:
            data["invitee"] = get_user_model().objects.get(
                disabled=False, email=data["email"]
            )
        except ObjectDoesNotExist:
            data["invitee"] = None
        except MultipleObjectsReturned:
            raise ValidationError(
                _("There is more than one user with the email '%(email)s'")
                % {"email": data["email"]}
            )

        if data["instance"].involved_applicants.filter(email=data["email"]).exists():
            raise ValidationError(
                _("Email '%(email)s' has already access to instance %(instance)s")
                % {"email": data["email"], "instance": data["instance"].pk}
            )

        return data

    class Meta:
        model = models.Applicant
        fields = ("user", "instance", "invitee", "created", "email")
        read_only_fields = ("user", "invitee", "created")
