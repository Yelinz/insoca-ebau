import pytest
from django.urls import reverse
from pytest_factoryboy import LazyFixture
from rest_framework import status


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
def test_applicant_list(admin_client, role, instance, django_assert_num_queries):
    url = reverse("applicant-list")

    with django_assert_num_queries(2):
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["data"]) == 1


def test_applicant_update(admin_client, instance):
    url = reverse("applicant-detail", args=[instance.involved_applicants.first().pk])

    response = admin_client.patch(url)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "role__name,instance__user,extra_applicants,expected_status",
    [
        ("Applicant", LazyFixture("admin_user"), 0, status.HTTP_403_FORBIDDEN),
        ("Applicant", LazyFixture("admin_user"), 1, status.HTTP_204_NO_CONTENT),
        ("Municipality", LazyFixture("admin_user"), 1, status.HTTP_403_FORBIDDEN),
        ("Service", LazyFixture("admin_user"), 1, status.HTTP_403_FORBIDDEN),
        ("Canton", LazyFixture("admin_user"), 1, status.HTTP_403_FORBIDDEN),
    ],
)
def test_applicant_delete(
    admin_client, role, instance, applicant_factory, extra_applicants, expected_status
):
    if extra_applicants:
        applicant_factory.create_batch(extra_applicants, instance=instance)

    url = reverse("applicant-detail", args=[instance.involved_applicants.first().pk])

    response = admin_client.delete(url)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "role__name,instance__user,created_email,passed_email,expected_status",
    [
        (
            "Applicant",
            LazyFixture("admin_user"),
            "test@example.com",
            "test@example.com",
            status.HTTP_201_CREATED,
        ),
        (
            "Applicant",
            LazyFixture("admin_user"),
            "test@example.com",
            "exists@example.com",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            "Applicant",
            LazyFixture("admin_user"),
            "test@example.com",
            "doesnotexist@example.com",
            status.HTTP_201_CREATED,
        ),
        (
            "Municipality",
            LazyFixture("admin_user"),
            "test@example.com",
            "test@example.com",
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "Service",
            LazyFixture("admin_user"),
            "test@example.com",
            "test@example.com",
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "Canton",
            LazyFixture("admin_user"),
            "test@example.com",
            "test@example.com",
            status.HTTP_403_FORBIDDEN,
        ),
    ],
)
def test_applicant_create(
    admin_client,
    user_factory,
    role,
    instance,
    applicant_factory,
    created_email,
    passed_email,
    expected_status,
    settings,
    notification_template,
):
    settings.APPLICATION["NOTIFICATIONS"]["APPLICANT"]["NEW"] = notification_template.pk
    settings.APPLICATION["NOTIFICATIONS"]["APPLICANT"][
        "EXISTING"
    ] = notification_template.pk

    url = reverse("applicant-list")

    applicant_factory(
        instance=instance,
        invitee=user_factory(email="exists@example.com"),
        email="exists@example.com",
    )

    user_factory(email=created_email)

    response = admin_client.post(
        url,
        data={
            "data": {
                "type": "applicants",
                "attributes": {"email": passed_email},
                "relationships": {
                    "instance": {"data": {"id": instance.pk, "type": "instances"}}
                },
            }
        },
    )

    assert response.status_code == expected_status

    if response.status_code == status.HTTP_201_CREATED:
        assert response.json()["data"]["relationships"]["user"]


@pytest.mark.parametrize("instance__user", [LazyFixture("admin_user")])
def test_applicant_create_multiple_users(admin_client, instance, user_factory):
    url = reverse("applicant-list")

    user_factory(email="test@example.com")
    user_factory(email="test@example.com")

    response = admin_client.post(
        url,
        data={
            "data": {
                "type": "applicants",
                "attributes": {"email": "test@example.com"},
                "relationships": {
                    "instance": {"data": {"id": instance.pk, "type": "instances"}}
                },
            }
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
