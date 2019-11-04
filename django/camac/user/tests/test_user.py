import pytest
from django.urls import reverse
from rest_framework import status


def test_check_password(admin_user):
    assert admin_user.check_password("password")
    assert not admin_user.check_password("invalid")


def test_get_full_name(admin_user):
    admin_user.name = "Muster"
    admin_user.surname = "Hans"

    assert admin_user.get_full_name() == "Muster Hans"


def test_me(admin_client, admin_user):
    admin_user.groups.all().delete()
    url = reverse("me")

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["data"]["attributes"]["username"] == admin_user.username


def test_me_group(admin_client, admin_user, service):
    url = reverse("me")

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert json["data"]["relationships"]["service"]["data"]["id"] == str(service.pk)


@pytest.mark.parametrize(
    "role__name,size",
    [("Applicant", 0), ("Service", 1), ("Canton", 1), ("Municipality", 1)],
)
def test_user_list(admin_client, size):
    url = reverse("user-list")

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == size


@pytest.mark.parametrize("role__name,size", [("Service", 1), ("Municipality", 0)])
def test_user_role_filter(admin_client, admin_user, group, user_group_factory, size):
    url = reverse("user-list")

    response = admin_client.get(url, {"exclude_role": "Municipality"})
    assert response.status_code == status.HTTP_200_OK
    json = response.json()
    assert len(json["data"]) == size
