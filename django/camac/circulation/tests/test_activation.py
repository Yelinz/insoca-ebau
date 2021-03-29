import functools

import pyexcel
import pytest
from django.urls import reverse
from pytest_factoryboy import LazyFixture
from rest_framework import status

from camac.circulation import serializers


@pytest.mark.parametrize(
    "role__name,instance__user,num_queries",
    [
        ("Applicant", LazyFixture("admin_user"), 6),
        ("Canton", LazyFixture("user"), 6),
        ("Municipality", LazyFixture("user"), 6),
        ("Service", LazyFixture("user"), 6),
    ],
)
def test_activation_list(
    admin_client, activation, num_queries, django_assert_num_queries
):
    url = reverse("activation-list")

    included = serializers.ActivationSerializer.included_serializers
    with django_assert_num_queries(num_queries):
        response = admin_client.get(url, data={"include": ",".join(included.keys())})
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["id"] == str(activation.pk)
    assert len(json["included"]) == len(included)


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_activation_detail(admin_client, activation):
    url = reverse("activation-detail", args=[activation.pk])

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize("role__name", ["Canton"])
def test_activation_export(
    admin_client,
    user,
    activation_factory,
    django_assert_num_queries,
    form_field_factory,
):
    url = reverse("activation-export")
    activations = activation_factory.create_batch(2)
    instance = activations[0].circulation.instance

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
    assert len(sheet) == len(activations)
    row = sheet[0]
    assert row[4] == "Muster Hans, Beispiel Jean"
    assert row[5] == "Bezeichnung"
