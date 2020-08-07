import inspect
import logging
from dataclasses import dataclass

import pytest
from caluma.caluma_core.faker import MultilangProvider
from caluma.caluma_form import factories as caluma_form_factories
from caluma.caluma_workflow import factories as caluma_workflow_factories
from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from factory import Faker
from factory.base import FactoryMetaClass
from pytest_factoryboy import register
from pytest_factoryboy.fixture import get_model_name
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from camac.applicants import factories as applicant_factories
from camac.core import factories as core_factories
from camac.document import factories as document_factories
from camac.document.tests.data import django_file
from camac.echbern import factories as ech_factories
from camac.faker import FreezegunAwareDatetimeProvider
from camac.instance import factories as instance_factories
from camac.notification import factories as notification_factories
from camac.objection import factories as objection_factories
from camac.responsible import factories as responsible_factories
from camac.user import factories as user_factories
from camac.user.authentication import CalumaInfo
from camac.user.models import Group, User
from camac.utils import build_url


def register_module(module, prefix=""):
    for name, obj in inspect.getmembers(module):
        if isinstance(obj, FactoryMetaClass) and not obj._meta.abstract:
            if prefix:
                # This prefixes only the model fixtures, not the factories
                model_name = get_model_name(obj)
                register(obj, _name=f"{prefix}_{model_name}")
            else:
                register(obj)


factory_logger = logging.getLogger("factory")
factory_logger.setLevel(logging.INFO)

sorl_thumbnail_logger = logging.getLogger("sorl.thumbnail")
sorl_thumbnail_logger.setLevel(logging.INFO)

register_module(user_factories)
register_module(instance_factories)
register_module(core_factories)
register_module(document_factories)
register_module(notification_factories)
register_module(applicant_factories)
register_module(responsible_factories)
register_module(ech_factories)
register_module(objection_factories)

# caluma factories
register_module(caluma_form_factories, prefix="caluma")
register_module(caluma_workflow_factories, prefix="caluma")

# TODO: Somehow the ordering of those two calls is relevant.
# Need to figure out why exactly (FreezegunAwareDatetimeProvider's
# methods aren't invoked if it's added first). This is some weird
# bug that I couldn't track down yet.
Faker.add_provider(MultilangProvider)
Faker.add_provider(FreezegunAwareDatetimeProvider)


@dataclass
class FakeRequest:
    group: Group
    user: User


@pytest.fixture
def request_mock(mocker):
    request_mock = mocker.patch(
        "django.test.client.WSGIRequest.caluma_info",
        new_callable=mocker.PropertyMock,
        create=True,
    )
    request_mock.return_value = CalumaInfo(
        {
            "sub": "462afaba-aeb7-494a-8596-3497b81ed701",
            settings.OIDC_USERNAME_CLAIM: "foo",
        }
    )


@pytest.fixture
def rf(db):
    return APIRequestFactory()


@pytest.fixture
def admin_user(admin_user, group, group_location, user_group_factory):
    admin_user.username = "462afaba-aeb7-494a-8596-3497b81ed701"
    admin_user.surname = "Admin"
    admin_user.name = "User"
    admin_user.save()
    user_group_factory(group=group, user=admin_user, default_group=1)
    return admin_user


@pytest.fixture
def admin_client(db, admin_user, request_mock):
    """Return instance of a JSONAPIClient that is logged in as test user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    client.user = admin_user
    return client


@pytest.fixture
def application_settings(settings):
    application_dict = dict(settings.APPLICATION)
    # settings fixture only restores per attribute
    # so need to set copy of dict
    settings.APPLICATION = application_dict
    return application_dict


@pytest.fixture
def multilang(application_settings):
    application_settings["IS_MULTILINGUAL"] = True


@pytest.fixture
def use_caluma_form(application_settings):
    application_settings["FORM_BACKEND"] = "caluma"
    application_settings["CALUMA"] = {"FORM_PERMISSIONS": ["main", "sb1", "sb2", "nfd"]}


@pytest.fixture
def ech_mandatory_answers_baugesuch():
    return {
        "ech-subject": "Baugesuch",
        "gemeinde": "Testgemeinde",
        "parzelle": [{"parzellennummer": "1586"}],
        "personalien-gesuchstellerin": [
            {
                "name-gesuchstellerin": "Testname",
                "ort-gesuchstellerin": "Testort",
                "plz-gesuchstellerin": 2323,
                "strasse-gesuchstellerin": "Teststrasse",
                "vorname-gesuchstellerin": "Testvorname",
                "juristische-person-gesuchstellerin": "Nein",
            }
        ],
    }


@pytest.fixture
def ech_mandatory_answers_einfache_vorabklaerung():
    return {
        "ech-subject": "Einfache Vorabklärung",
        "gemeinde": "Testgemeinde",
        "name-gesuchstellerin-vorabklaerung": "Testname",
        "ort-gesuchstellerin": "Testort",
        "plz-gesuchstellerin": 23235,  # non standard swiss zip
        "strasse-gesuchstellerin": "Teststrasse",
        "vorname-gesuchstellerin-vorabklaerung": "Testvorname",
    }


@pytest.fixture
def ech_mandatory_answers_vollstaendige_vorabklaerung():
    return {
        "ech-subject": "Vollständige Vorabklärung",
        "gemeinde": "Testgemeinde",
        "personalien-gesuchstellerin": [
            {
                "name-gesuchstellerin": "Testname",
                "ort-gesuchstellerin": "Testort",
                "plz-gesuchstellerin": 232,  # non standard swiss zip
                "strasse-gesuchstellerin": "Teststrasse",
                "vorname-gesuchstellerin": "Testvorname",
                "juristische-person-gesuchstellerin": "Nein",
            }
        ],
    }


@pytest.fixture
def caluma_config_bern(db):
    """
    Load the caluma config for kt_bern.

    Execution of this fixture takes some time. Only use if really necessary.
    """
    call_command("loaddata", settings.ROOT_DIR("kt_bern/config-caluma-form.json"))
    call_command("loaddata", settings.ROOT_DIR("kt_bern/config-caluma-workflow.json"))


@pytest.fixture
def support_role(role):
    role.name = "support"
    role.save()
    return role


@pytest.fixture
def system_operation_group(support_role, group):
    group.role = support_role
    group.name = "System-Betrieb"
    group.save()
    return group


@pytest.fixture
def system_operation_user(system_operation_group, user, user_group_factory):
    user_group_factory(group=system_operation_group, user=user, default_group=1)
    user.username = "System-Betrieb"
    user.save()
    return user


@pytest.fixture(autouse=True)
def media_root(tmpdir_factory, settings):
    """Set django's MEDIA_ROOT setting to a temporary directory.

    Otherwise all files that get stored through File- and ImageFields would
    get stored in the project root and pollute it.
    """
    settings.MEDIA_ROOT = tmpdir_factory.mktemp("media_root")


@pytest.fixture
def clear_cache():
    cache.clear()


@pytest.fixture
def unoconv_pdf_mock(requests_mock):
    requests_mock.register_uri(
        "POST",
        build_url(settings.UNOCONV_URL, "/unoconv/pdf"),
        content=django_file("multiple-pages.pdf").read(),
    )


@pytest.fixture
def unoconv_invalid_mock(requests_mock):
    requests_mock.register_uri(
        "POST",
        build_url(settings.UNOCONV_URL, "/unoconv/invalid"),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@pytest.fixture
def nfd_completion_date(
    activation, camac_question_factory, camac_chapter_factory, activation_answer_factory
):
    """Return a sample nfd completion date.

    In Uri the nfd completion date gets set after a service has completed the
    "Nachforderung" process on an instance with an activation.
    """
    return activation_answer_factory(
        chapter=camac_chapter_factory(pk=41),
        question=camac_question_factory(pk=243),
        item=1,
        activation=activation,
        answer=timezone.now(),
    )
