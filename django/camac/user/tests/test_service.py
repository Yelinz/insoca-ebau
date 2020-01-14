import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.parametrize(
    "role__name,size",
    [("Applicant", 0), ("Service", 1), ("Canton", 1), ("Municipality", 1)],
)
def test_service_list(admin_client, service, size):
    url = reverse("service-list")

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == size
    if size > 0:
        assert json["data"][0]["attributes"]["name"] == service.name
        assert json["data"][0]["attributes"]["city"] == service.get_trans_attr("city")


@pytest.mark.parametrize(
    "role__name",
    [
        "Municipality" 
    ],
)
def test_service_filter(admin_client, service_factory):
    service = service_factory()
    url = f"{reverse('service-list')}?name={service.name}"

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == 1


@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Applicant", status.HTTP_404_NOT_FOUND),
        ("Municipality", status.HTTP_200_OK),
        ("Canton", status.HTTP_200_OK),
        ("Service", status.HTTP_200_OK),
    ],
)
def test_service_update(admin_client, service, status_code):
    url = reverse("service-detail", args=[service.pk])
    response = admin_client.patch(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Applicant", status.HTTP_403_FORBIDDEN),
        ("Municipality", status.HTTP_403_FORBIDDEN),
        ("Canton", status.HTTP_403_FORBIDDEN),
        ("Service", status.HTTP_403_FORBIDDEN),
    ],
)
def test_service_delete(admin_client, service, status_code):
    url = reverse("service-detail", args=[service.pk])
    response = admin_client.delete(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "service_t__name,service_t__language", [("je ne sais pas", "fr")]
)
@pytest.mark.parametrize(
    "role__name,size", [("Applicant", 0), ("Canton", 1), ("Service", 1)]
)
def test_service_list_multilingual(admin_client, service_t, size, multilang):
    url = reverse("service-list")

    response = admin_client.get(url, HTTP_ACCEPT_LANGUAGE=service_t.language)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == size
    if size > 0:
        assert json["data"][0]["attributes"]["name"] == service_t.name
