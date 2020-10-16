import datetime
import functools

import pyexcel
import pytest
import pytz
from caluma.caluma_form import models as caluma_form_models
from caluma.caluma_user.models import BaseUser
from caluma.caluma_workflow import api as workflow_api, models as caluma_workflow_models
from django.urls import reverse
from pytest_factoryboy import LazyFixture
from rest_framework import status

from camac.core.models import InstanceLocation, WorkflowEntry
from camac.instance import serializers


@pytest.mark.parametrize(
    "instance_state__name,instance__creation_date",
    [("new", "2018-04-17T09:31:56+02:00")],
)
@pytest.mark.parametrize(
    "role__name,instance__user,num_queries,editable",
    [
        ("Applicant", LazyFixture("admin_user"), 17, {"instance", "form", "document"}),
        # reader should see instances from other users but has no editables
        ("Reader", LazyFixture("user"), 17, set()),
        ("Canton", LazyFixture("user"), 17, {"form", "document"}),
        ("Municipality", LazyFixture("user"), 17, {"form", "document"}),
        ("Service", LazyFixture("user"), 17, {"document"}),
        ("Coordination", LazyFixture("user"), 17, {"form", "document"}),
    ],
)
def test_instance_list(
    application_settings,
    admin_client,
    instance,
    activation,
    num_queries,
    group,
    django_assert_num_queries,
    editable,
    group_location_factory,
    instance_service_factory,
    circulation_factory,
    activation_factory,
):
    application_settings["INSTANCE_ACCESS_TYPE_ROLES"] = {
        "municipality": ["Municipality"],
        "service": ["Service"],
    }

    url = reverse("instance-list")

    # verify that two locations may be assigned to group
    group_location_factory(group=group)

    service = instance_service_factory(instance=instance).service
    circulation = circulation_factory(service=service)
    activation_factory(service=service, circulation=circulation)

    included = serializers.InstanceSerializer.included_serializers
    with django_assert_num_queries(num_queries):
        response = admin_client.get(
            url,
            data={
                "include": ",".join(included.keys()),
                "creation_date_before": "17.04.2018",
                "creation_date_after": "17.04.2018",
            },
        )
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["id"] == str(instance.pk)
    assert set(json["data"][0]["meta"]["editable"]) == set(editable)
    # included previous_instance_state and instance_state are the same
    assert len(json["included"]) == len(included) - 1


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_instance_detail(admin_client, instance):
    url = reverse("instance-detail", args=[instance.pk])

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("instance__identifier", ["00-00-000"])
@pytest.mark.parametrize("form_field__name", ["name"])
@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
@pytest.mark.parametrize(
    "form_field__value,search",
    [
        ("simpletext", "simple"),
        (["list", "value"], "list"),
        ({"key": ["l-list-d", ["b-list-d"]]}, "list"),
    ],
)
def test_instance_search(admin_client, instance, form_field, search):
    url = reverse("instance-list")

    response = admin_client.get(url, {"search": search})
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["id"] == str(instance.pk)


@pytest.mark.parametrize("role__name", [("Support")])
def test_instance_search_sanctions(
    db, application_settings, instance, sanction_factory, instance_factory, admin_client
):
    """Test that instances can be filtered by sanction creator and sanction
    control instance.
    """

    application_settings["FORM_BACKEND"] = "caluma"

    sanction = sanction_factory(instance=instance)

    # The following instance should not turn up in the results.
    instance_factory()

    filters = [
        {"sanction_creator": sanction.service.pk},
        {"sanction_control_instance": sanction.control_instance.pk},
    ]

    for search_filter in filters:
        url = reverse("instance-list")
        response = admin_client.get(url, search_filter)
        assert response.status_code == status.HTTP_200_OK
        json = response.json()
        assert len(json["data"]) == 1
        assert json["data"][0]["id"] == str(instance.pk)


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_instance_filter_fields(admin_client, instance, form_field_factory):

    filters = {}

    for i in range(4):
        value = str(i)
        form_field_factory(name=value, value=value, instance=instance)
        filters["fields[" + value + "]"] = value

    url = reverse("instance-list")

    response = admin_client.get(url, filters)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == 1


@pytest.mark.parametrize(
    "instance_state__name,instance__identifier", [("new", "00-00-000")]
)
@pytest.mark.parametrize(
    "role__name,instance__user,status_code",
    [
        # applicant/reader can't update their own Instance,
        # but might update FormField etc.
        ("Applicant", LazyFixture("admin_user"), status.HTTP_400_BAD_REQUEST),
        ("Reader", LazyFixture("user"), status.HTTP_403_FORBIDDEN),
        ("Canton", LazyFixture("user"), status.HTTP_403_FORBIDDEN),
        ("Municipality", LazyFixture("user"), status.HTTP_403_FORBIDDEN),
        ("Service", LazyFixture("user"), status.HTTP_404_NOT_FOUND),
        ("Unknown", LazyFixture("user"), status.HTTP_404_NOT_FOUND),
        ("Coordination", LazyFixture("user"), status.HTTP_403_FORBIDDEN),
    ],
)
def test_instance_update(
    admin_client, instance, location_factory, form_factory, status_code
):
    url = reverse("instance-detail", args=[instance.pk])

    data = {
        "data": {
            "type": "instances",
            "id": instance.pk,
            "relationships": {
                "form": {"data": {"type": "forms", "id": form_factory().pk}},
                "location": {
                    "data": {"type": "locations", "id": location_factory().pk}
                },
            },
        }
    }

    response = admin_client.patch(url, data=data)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,instance__user,instance_state__name",
    [("Applicant", LazyFixture("admin_user"), "new")],
)
def test_instance_update_location(admin_client, instance, location_factory):
    url = reverse("instance-detail", args=[instance.pk])

    new_location = location_factory()

    data = {
        "data": {
            "type": "instances",
            "id": instance.pk,
            "relationships": {
                "location": {"data": {"type": "locations", "id": new_location.pk}}
            },
        }
    }

    response = admin_client.patch(url, data=data)
    assert response.status_code == status.HTTP_200_OK

    assert InstanceLocation.objects.filter(
        instance=instance, location=new_location
    ).exists()


@pytest.mark.parametrize(
    "role__name,instance__user,instance_state__name,status_code",
    [
        ("Applicant", LazyFixture("admin_user"), "new", status.HTTP_204_NO_CONTENT),
        ("Applicant", LazyFixture("admin_user"), "subm", status.HTTP_403_FORBIDDEN),
        ("Reader", LazyFixture("admin_user"), "new", status.HTTP_204_NO_CONTENT),
        ("Canton", LazyFixture("user"), "new", status.HTTP_403_FORBIDDEN),
        ("Municipality", LazyFixture("user"), "new", status.HTTP_403_FORBIDDEN),
        ("Service", LazyFixture("user"), "new", status.HTTP_404_NOT_FOUND),
        ("Unknown", LazyFixture("user"), "new", status.HTTP_404_NOT_FOUND),
    ],
)
def test_instance_destroy(admin_client, instance, status_code, location_factory):
    url = reverse("instance-detail", args=[instance.pk])

    """
    Add InstanceLocation relationship to make sure it also will be deleted
    when the instance is deleted (cascade deletion).
    """
    instance_location = InstanceLocation.objects.create(
        location=location_factory(), instance=instance
    )

    response = admin_client.delete(url)

    assert response.status_code == status_code

    # verify deleted InstanceLocation if api query was successful
    if response.status_code == status.HTTP_204_NO_CONTENT:
        assert not InstanceLocation.objects.filter(id=instance_location.pk).exists()


@pytest.mark.parametrize(
    "instance_state__name,instance__location",
    [("new", None), ("new", LazyFixture("location"))],
)
def test_instance_create(
    admin_client, admin_user, form, instance_state, instance, caluma_workflow_config_sz
):
    url = reverse("instance-list")

    location_data = (
        {"type": "locations", "id": instance.location.pk} if instance.location else None
    )

    data = {
        "data": {
            "type": "instances",
            "id": None,
            "relationships": {
                "form": {"data": {"type": "forms", "id": form.pk}},
                "location": {"data": location_data},
            },
        }
    }

    response = admin_client.post(url, data=data)
    assert response.status_code == status.HTTP_201_CREATED

    json = response.json()

    url = reverse("instance-list")
    response = admin_client.post(url, data=json)
    assert response.status_code == status.HTTP_201_CREATED

    assert json["data"]["attributes"]["modification-date"] < (
        response.json()["data"]["attributes"]["modification-date"]
    )

    if instance.location:
        assert InstanceLocation.objects.filter(
            instance_id=json["data"]["id"], location=instance.location
        ).exists()


@pytest.mark.freeze_time("2017-7-27")
@pytest.mark.parametrize(
    "instance__user,location__communal_federal_number,instance_state__name",
    [(LazyFixture("admin_user"), "1311", "new")],
)
@pytest.mark.parametrize("attachment__question", ["dokument-parzellen"])
@pytest.mark.parametrize("short_dossier_number", [True, False])
@pytest.mark.parametrize(
    "role__name,instance__location,form__name,status_code",
    [
        ("Applicant", LazyFixture("location"), "baugesuch", status.HTTP_200_OK),
        ("Applicant", LazyFixture("location"), "", status.HTTP_400_BAD_REQUEST),
        ("Applicant", None, "baugesuch", status.HTTP_400_BAD_REQUEST),
        (
            "Applicant",
            LazyFixture(lambda location_factory: location_factory()),
            "baugesuch",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            "Applicant",
            LazyFixture("location"),
            "geschaeftskontrolle",
            status.HTTP_200_OK,
        ),
        ("Applicant", LazyFixture("location"), "baugesuch", status.HTTP_200_OK),
    ],
)
def test_instance_submit(
    admin_client,
    admin_user,
    form,
    form_field_factory,
    instance,
    instance_state,
    instance_state_factory,
    status_code,
    role_factory,
    group_factory,
    settings,
    group_location_factory,
    attachment,
    workflow_item,
    notification_template,
    mailoutbox,
    attachment_section,
    attachment_section_group_acl_factory,
    role,
    short_dossier_number,
    mocker,
    unoconv_pdf_mock,
    caluma_workflow_config_sz,
):

    settings.APPLICATION["NOTIFICATIONS"]["SUBMIT"] = notification_template.slug
    settings.APPLICATION["WORKFLOW_ITEMS"]["SUBMIT"] = workflow_item.pk
    settings.APPLICATION["INSTANCE_IDENTIFIER_FORM_ABBR"] = {"vbs": "PV"}
    settings.APPLICATION["SHORT_DOSSIER_NUMBER"] = short_dossier_number

    case = workflow_api.start_case(
        workflow=caluma_workflow_models.Workflow.objects.get(pk="building-permit"),
        form=caluma_form_models.Form.objects.get(pk="baugesuch"),
        meta={"camac-instance-id": instance.pk},
        user=BaseUser(),
    )

    # only create group in a successful run
    if status_code == status.HTTP_200_OK:
        group = group_factory(role=role_factory(name="Municipality"))
        group_location_factory(group=group, location=instance.location)
        attachment_section_group_acl_factory(
            group=admin_user.groups.first(), attachment_section=attachment_section
        )

    instance_state_factory(name="subm")
    url = reverse("instance-submit", args=[instance.pk])
    add_field = functools.partial(form_field_factory, instance=instance)

    add_field(name="kategorie-des-vorhabens", value=["Anlage(n)"])
    add_field(name="hohe-der-anlage", value=12.5)
    add_field(name="hohe-der-anlage-gte", value="Test")
    add_field(name="kosten-der-anlage", value=10001)
    add_field(name="kosten-der-anlage-gt", value="Test")
    add_field(name="tiefe-der-bohrung", value=10)
    add_field(name="tiefe-der-bohrung-lte", value="Test")
    add_field(name="durchmesser-der-bohrung", value=9)
    add_field(name="durchmesser-der-bohrung-lt", value="Test")
    add_field(name="bezeichnung", value="Bezeichnung")
    add_field(name="bewilligung-bohrung", value="Ja")
    add_field(name="bohrungsdaten", value="Test")
    add_field(name="anlagen-mit-erheblichen-schadstoffemissionen", value="Ja")
    add_field(name="anlagen-mit-erheblichen-schadstoffemissionen-welche", value="Test")
    add_field(name="grundeigentumerschaft", value=[{"name": "Bund"}])
    add_field(name="gwr", value=[{"name": "Name", "wohnungen": [{"stockwerk": "1OG"}]}])
    add_field(
        name="punkte", value=[[{"lat": 47.02433179952733, "lng": 8.634144559228435}]]
    )
    if form.name == "geschaeftskontrolle":
        add_field(name="meta", value='{"formType": "vbs"}')

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {"demo": {role.name.lower(): {"admin": [attachment_section.pk]}}},
    )

    response = admin_client.post(url)
    assert response.status_code == status_code, response.content

    if status_code == status.HTTP_200_OK:
        json = response.json()

        identifier = "11-17-001" if short_dossier_number else "1311-17-001"
        if form.name == "geschaeftskontrolle":
            identifier = "PV-17-001"

        assert json["data"]["attributes"]["identifier"] == identifier
        assert set(json["data"]["meta"]["editable"]) == set()

        instance.refresh_from_db()
        assert instance.instance_state.name == "subm"

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        mail.subject == notification_template.subject

        assert WorkflowEntry.objects.filter(
            instance=instance, workflow_item=workflow_item
        ).exists()

        assert case.work_items.filter(task_id="submit", status="completed").exists()


@pytest.mark.parametrize("role__name", ["Canton"])
def test_instance_export_list(
    admin_client, user, instance_factory, django_assert_num_queries, form_field_factory
):
    url = reverse("instance-export-list")
    instances = instance_factory.create_batch(2, user=user)
    instance = instances[0]

    add_field = functools.partial(form_field_factory, instance=instance)
    add_field(
        name="projektverfasser-planer",
        value=[{"name": "Muster Hans"}, {"name": "Beispiel Jean"}],
    )
    add_field(name="bezeichnung", value="Bezeichnung")

    with django_assert_num_queries(2):
        response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    book = pyexcel.get_book(file_content=response.content, file_type="xlsx")
    # bookdict is a dict of tuples(name, content)
    sheet = book.bookdict.popitem()[1]
    assert len(sheet) == len(instances)
    row = sheet[0]
    assert "Muster Hans, Beispiel Jean" in row
    assert "Bezeichnung" in row


@pytest.mark.parametrize("attachment__question", ["dokument-parzellen"])
@pytest.mark.parametrize(
    "role__name,instance__user,form__name,status_code,to_type",
    [
        (
            "Applicant",
            LazyFixture("admin_user"),
            "baugesuch",
            status.HTTP_200_OK,
            "docx",
        ),
        (
            "Applicant",
            LazyFixture("admin_user"),
            "baugesuch",
            status.HTTP_200_OK,
            "pdf",
        ),
        (
            "Applicant",
            LazyFixture("admin_user"),
            "baugesuch",
            status.HTTP_400_BAD_REQUEST,
            "invalid",
        ),
    ],
)
def test_instance_export_detail(
    application_settings,
    admin_client,
    form,
    instance,
    form_field_factory,
    status_code,
    to_type,
    attachment,
    unoconv_pdf_mock,
    unoconv_invalid_mock,
):
    application_settings["COORDINATE_QUESTION"] = "punkte"

    url = reverse("instance-export-detail", args=[instance.pk])

    add_field = functools.partial(form_field_factory, instance=instance)
    add_field(
        name="grundeigentumerschaft",
        value=[{"name": "Muster Hans"}, {"name": "Beispiel Jean"}],
    )
    add_field(name="bohrungsdaten", value="Bezeichnung")
    add_field(name="kategorie-des-vorhabens", value=["Anlage(n)", "Baute(n)"])
    add_field(name="baugeruest-errichtet-am", value="2019-20-19")
    add_field(
        name="punkte", value=[{"lat": 47.02433179952733, "lng": 8.634144559228435}]
    )

    response = admin_client.get(url, data={"type": to_type})
    assert response.status_code == status_code


@pytest.mark.freeze_time("2017-7-27")
@pytest.mark.parametrize("short_dossier_number", [True, False])
@pytest.mark.parametrize("use_caluma", [True, False])
@pytest.mark.parametrize("location__communal_federal_number", ["1311"])
def test_instance_generate_identifier(
    db,
    instance,
    instance_factory,
    case_factory,
    application_settings,
    short_dossier_number,
    use_caluma,
):
    application_settings["CALUMA"]["SAVE_DOSSIER_NUMBER_IN_CALUMA"] = use_caluma
    application_settings["SHORT_DOSSIER_NUMBER"] = short_dossier_number

    prefix = "" if short_dossier_number else "13"
    identifier = prefix + "11-17-010"
    if use_caluma:
        case_factory(
            meta={"camac-instance-id": instance.pk, "dossier-number": identifier}
        )
    else:
        instance_factory(identifier=identifier)

    new_identifier = serializers.generate_identifier(instance)

    assert new_identifier == prefix + "11-17-011"


@pytest.mark.freeze_time("2017-7-27")
@pytest.mark.parametrize(
    "role__name,instance__user,publication_entry__publication_date,publication_entry__is_published,status_code",
    [
        (
            "Municipality",
            LazyFixture("admin_user"),
            datetime.datetime(2016, 6, 28, tzinfo=pytz.UTC),
            True,
            status.HTTP_200_OK,
        ),
        (
            "PublicReader",
            LazyFixture("admin_user"),
            datetime.datetime(2017, 6, 28, tzinfo=pytz.UTC),
            True,
            status.HTTP_200_OK,
        ),
        (
            "PublicReader",
            LazyFixture("admin_user"),
            datetime.datetime(2017, 6, 26, tzinfo=pytz.UTC),
            True,
            status.HTTP_404_NOT_FOUND,
        ),
        (
            "PublicReader",
            LazyFixture("admin_user"),
            datetime.datetime(2017, 6, 28, tzinfo=pytz.UTC),
            False,
            status.HTTP_404_NOT_FOUND,
        ),
    ],
)
def test_instance_detail_publication(
    admin_client, instance, publication_entry, status_code
):
    url = reverse("instance-detail", args=[instance.pk])

    response = admin_client.get(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_circulation_state_filter(
    application_settings,
    admin_client,
    instance,
    circulation,
    activation,
    circulation_state,
):

    url = reverse("instance-list")

    state_search = circulation_state.pk

    # first, ensure the instance is found with the correct instance state id
    response = admin_client.get(url, {"circulation_state": state_search})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["data"]) == 1

    # second, make sure that it doesn't show up with another instance id
    response = admin_client.get(url, {"circulation_state": circulation_state.pk + 1})
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["data"]) == 0


@pytest.mark.parametrize("role__name,", [("Applicant")])
def test_tags_filter(admin_client, admin_user, instance_factory):

    inst_a, inst_b, inst_c = instance_factory.create_batch(3, user=admin_user)
    tag_args = dict(service=admin_user.groups.first().service)

    inst_a.tags.create(name="foo", **tag_args)
    inst_a.tags.create(name="bar", **tag_args)
    inst_b.tags.create(name="bar", **tag_args)
    inst_b.tags.create(name="baz", **tag_args)
    inst_c.tags.create(name="bla", **tag_args)

    url = reverse("instance-list")

    search_expectations = {
        "": [inst_a, inst_b, inst_c],  # "empty" search should list all
        "foo": [inst_a],
        "bar": [inst_a, inst_b],
        "foo,bar": [inst_a],
        "baz,bar": [inst_b],
    }

    for search, expectation in search_expectations.items():
        response = admin_client.get(url, {"tags": search})
        assert response.status_code == status.HTTP_200_OK

        data = response.json()["data"]
        got_ids = set([row["id"] for row in data])
        expect_ids = set([str(inst.pk) for inst in expectation])
        assert got_ids == expect_ids


@pytest.mark.parametrize(
    "role__name,instance_state__name,responsible_service__responsible_user,responsible_service__service, instance_service__active",
    [("Service", "new", LazyFixture("user"), LazyFixture("service"), 1)],
)
def test_responsible_service_filters(
    admin_client,
    user,
    user_factory,
    instance,
    instance_factory,
    group,
    service,
    service_factory,
    instance_service,
    instance_service_factory,
    responsible_service,
    responsible_service_factory,
    circulation_factory,
    activation,
    activation_factory,
):
    url = reverse("instance-list")

    response = admin_client.get(url)
    # can see the instance
    assert response.status_code == status.HTTP_200_OK

    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == str(instance.pk)

    # service is responsible for instance
    other_service = service_factory()
    response = admin_client.get(url, data={"responsible_service": service.pk})
    data = response.json()["data"]
    assert len(data) == 1
    assert int(data[0]["id"]) == instance.pk

    # other service has no instances responsible for
    other_service = service_factory()
    response = admin_client.get(url, data={"responsible_service": other_service.pk})
    assert len(response.json()["data"]) == 0

    # user is responsible for this service
    response = admin_client.get(url, data={"responsible_service_user": user.pk})
    data = response.json()["data"]
    assert len(data) == 1
    assert int(data[0]["id"]) == instance.pk

    # no instance is left without responsible user
    response = admin_client.get(url, data={"responsible_service_user": "nobody"})
    data = response.json()["data"]
    assert len(data) == 0

    # create other_instance which is visible for "service"
    other_instance = instance_factory(instance_state__name="subm")
    activation_factory(
        circulation=circulation_factory(instance=other_instance), service=service
    )
    instance_service_factory(instance=other_instance, service=service)

    # other_instance has no responsible user
    response = admin_client.get(url, data={"responsible_service_user": "nobody"})
    data = response.json()["data"]
    assert len(data) == 1
    assert int(data[0]["id"]) == other_instance.pk

    other_user = user_factory()
    other_instance.responsible_services.create(
        service=other_service, responsible_user=other_user
    )

    # other_user of other_service is responsible, so not visible to "service"
    response = admin_client.get(url, data={"responsible_service_user": other_user.pk})
    data = response.json()["data"]
    assert len(data) == 0


@pytest.mark.parametrize(
    "role__name,instance__user", [("Municipality", LazyFixture("user"))]
)
def test_responsible_instance_user(
    admin_client, instance, user, service, service_factory
):

    instance.responsibilities.create(user=user, service=service)

    # First make sure we can find instances with given responsible user
    resp = admin_client.get(
        reverse("instance-list"), {"responsible_instance_user": str(user.pk)}
    )
    assert resp.status_code == status.HTTP_200_OK and resp.content
    assert len(resp.json()["data"]) == 1

    # "nobody" filter should return nothing if all instances have a responsible user
    resp = admin_client.get(
        reverse("instance-list"), {"responsible_instance_user": "NOBODY"}
    )
    assert resp.status_code == status.HTTP_200_OK and resp.content
    assert len(resp.json()["data"]) == 0

    # "nobody" filter should return instance where there is no responsible user
    instance.responsibilities.all().delete()
    resp = admin_client.get(
        reverse("instance-list"), {"responsible_instance_user": "NOBODY"}
    )
    assert resp.status_code == status.HTTP_200_OK and resp.content
    assert len(resp.json()["data"]) == 1

    # not set shouldn't do anything
    resp = admin_client.get(reverse("instance-list"), {"responsible_instance_user": ""})
    assert resp.status_code == status.HTTP_200_OK and resp.content
    assert len(resp.json()["data"]) == 1

    # different service shouldnt return anything
    instance.responsibilities.create(user=user, service=service_factory())
    resp = admin_client.get(
        reverse("instance-list"), {"responsible_instance_user": str(user.pk)}
    )
    assert resp.status_code == status.HTTP_200_OK and resp.content
    assert len(resp.json()["data"]) == 0


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_instance_filter_is_applicant(admin_client, instance):
    url = reverse("instance-list")

    response = admin_client.get(url, {"is_applicant": 1})
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == 1

    response = admin_client.get(url, {"is_applicant": 0})
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == 0


@pytest.mark.parametrize("role__name", ["Applicant"])
def test_instance_form_field_ordering(
    admin_client, admin_user, instance_factory, form_field_factory
):
    url = reverse("instance-list")

    instances = instance_factory.create_batch(2, user=admin_user)

    add_field = functools.partial(form_field_factory, instance=instances[0])
    add_field(name="bezeichnung", value="ABC")
    add_field = functools.partial(form_field_factory, instance=instances[1])
    add_field(name="bezeichnung", value="ZYX")

    response = admin_client.get(url, {"sort_form_field": "bezeichnung"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["id"] == str(instances[0].pk)
    assert data[1]["id"] == str(instances[1].pk)

    response = admin_client.get(url, {"sort_form_field": "-bezeichnung"})

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["id"] == str(instances[1].pk)
    assert data[1]["id"] == str(instances[0].pk)


@pytest.mark.parametrize("role__name", ["Coordination"])
@pytest.mark.parametrize("is_creator", [True, False])
@pytest.mark.parametrize("forbidden_states", [None, [9999999]])
def test_instance_list_coordination_created(
    db,
    mocker,
    admin_client,
    instance_state,
    instance,
    is_creator,
    group_factory,
    forbidden_states,
):
    """Ensure that the coordination role sees their correct dossiers.

    KOOR role can see dossiers which their group has created,
    or which are not in a forbidden state. Note that this is a workaround,
    as the acutal logic in PHP for this rule is rather more complicated,
    but we're not replicating that rule here (yet).
    """
    if forbidden_states is None:
        # unfortunately cannot parametrize this :(
        forbidden_states = [instance_state.pk]

    mocker.patch(
        "camac.constants.kt_uri.INSTANCE_STATES_HIDDEN_FOR_KOOR", forbidden_states
    )

    if not is_creator:
        other_group = group_factory()
        instance.group = other_group
        instance.save()

    url = reverse("instance-list")
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    if is_creator or forbidden_states == [9999999]:
        assert len(json["data"]) == 1
        assert json["data"][0]["id"] == str(instance.pk)
    else:
        assert len(json["data"]) == 0


@pytest.mark.parametrize("role__name", ["Commission"])
@pytest.mark.parametrize("has_assignment", [True, False])
def test_instance_list_commission(db, admin_client, has_assignment, request, instance):
    """Ensure that a commission only sees dossiers which they were invited on."""

    if has_assignment:
        request.getfixturevalue("commission_assignment")

    url = reverse("instance-list")
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    if has_assignment:
        assert len(json["data"]) == 1
        assert json["data"][0]["id"] == str(instance.pk)
    else:
        assert len(json["data"]) == 0
