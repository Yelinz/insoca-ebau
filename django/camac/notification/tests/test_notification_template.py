import json

import pytest
from django.urls import reverse
from pytest_factoryboy import LazyFixture
from rest_framework import status


@pytest.mark.parametrize(
    "role__name,num_queries,size,notification_template__type,notification_template__service",
    [
        ("Applicant", 1, 0, "email", LazyFixture("service")),
        ("Service", 2, 1, "email", LazyFixture("service")),
        ("Municipality", 2, 1, "email", None),
        ("Canton", 2, 1, "textcomponent", None),
        ("Service", 2, 1, "textcomponent", LazyFixture("service")),
    ],
)
def test_notification_template_list(
    admin_client, notification_template, num_queries, django_assert_num_queries, size
):
    url = reverse("notificationtemplate-list")
    with django_assert_num_queries(num_queries):
        response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    if size > 0:
        json = response.json()
        assert len(json["data"]) == size
        assert json["data"][0]["id"] == str(notification_template.pk)


@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Applicant", status.HTTP_404_NOT_FOUND),
        ("Municipality", status.HTTP_200_OK),
        ("Canton", status.HTTP_200_OK),
        ("Service", status.HTTP_200_OK),
    ],
)
def test_notification_template_update(admin_client, notification_template, status_code):
    url = reverse("notificationtemplate-detail", args=[notification_template.pk])
    response = admin_client.patch(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Applicant", status.HTTP_403_FORBIDDEN),
        ("Canton", status.HTTP_201_CREATED),
        ("Service", status.HTTP_201_CREATED),
        ("Municipality", status.HTTP_201_CREATED),
    ],
)
def test_notification_template_create(admin_client, notification_template, status_code):
    url = reverse("notificationtemplate-list")

    data = {
        "data": {
            "type": "notification-templates",
            "id": None,
            "attributes": {
                "body": "Test",
                "purpose": "Test",
                "type": "textcomponent",
                "subject": "Test",
            },
        }
    }

    response = admin_client.post(url, data=data)
    assert response.status_code == status_code
    if status_code == status.HTTP_201_CREATED:
        json = response.json()
        assert json["data"]["attributes"]["type"] == "textcomponent"


@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Applicant", status.HTTP_404_NOT_FOUND),
        ("Municipality", status.HTTP_204_NO_CONTENT),
        ("Canton", status.HTTP_204_NO_CONTENT),
        ("Service", status.HTTP_204_NO_CONTENT),
    ],
)
def test_notification_template_destroy(
    admin_client, notification_template, status_code
):
    url = reverse("notificationtemplate-detail", args=[notification_template.pk])

    response = admin_client.delete(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "notification_template__body", ["{{identifier}} {{answer_period_date}}"]
)
@pytest.mark.parametrize(
    "role__name,instance__identifier,notification_template__subject,status_code",
    [
        ("Canton", "identifier", "{{identifier}}", status.HTTP_200_OK),
        ("Canton", "identifier", "{{$invalid}}", status.HTTP_400_BAD_REQUEST),
    ],
)
@pytest.mark.freeze_time("2017-1-1")
def test_notification_template_merge(
    admin_client,
    instance,
    notification_template,
    status_code,
    activation,
    billing_entry,
    settings,
):
    url = reverse("notificationtemplate-merge", args=[notification_template.pk])

    response = admin_client.get(url, data={"instance": instance.pk})
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        json = response.json()
        assert json["data"]["attributes"]["subject"] == instance.identifier
        assert json["data"]["attributes"]["body"] == "identifier 21.01.2017"
        assert json["data"]["id"] == "{0}-{1}".format(
            notification_template.pk, instance.pk
        )
        assert json["data"]["type"] == "notification-template-merges"


@pytest.mark.parametrize(
    "user__email,service__email", [("user@example.com", "service@example.com")]
)
@pytest.mark.parametrize(
    "notification_template__subject,instance__identifier",
    [("{{identifier}}", "identifer")],
)
@pytest.mark.parametrize(
    "role__name,status_code",
    [
        ("Canton", status.HTTP_204_NO_CONTENT),
        ("Municipality", status.HTTP_204_NO_CONTENT),
        ("Service", status.HTTP_204_NO_CONTENT),
        ("Applicant", status.HTTP_400_BAD_REQUEST),
    ],
)
def test_notification_template_sendmail(
    admin_client,
    instance,
    notification_template,
    status_code,
    mailoutbox,
    activation,
    settings,
):
    url = reverse("notificationtemplate-sendmail", args=[notification_template.pk])

    data = {
        "data": {
            "type": "notification-template-sendmails",
            "id": None,
            "attributes": {
                "body": "Test body",
                "recipient-types": ["applicant", "municipality", "service"],
            },
            "relationships": {
                "instance": {"data": {"type": "instances", "id": instance.pk}}
            },
        }
    }

    response = admin_client.post(url, data=data)
    assert response.status_code == status_code
    if status_code == status.HTTP_204_NO_CONTENT:
        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert set(mail.bcc) == {
            "user@example.com",
            "service@example.com",
            "service@example.com",
        }
        assert mail.subject == settings.EMAIL_PREFIX_SUBJECT + instance.identifier
        assert mail.body == settings.EMAIL_PREFIX_BODY + "Test body"


@pytest.mark.parametrize(
    "user__email,role__name,notification_template__subject",
    [
        (
            "user@example.com",
            "Municipality",
            "{{FORM_NAME}} {{EBAU_NUMBER}} ({{INSTANCE_ID}})",
        )
    ],
)
def test_notification_caluma_placeholders(
    admin_client,
    instance,
    notification_template,
    mailoutbox,
    activation,
    settings,
    requests_mock,
    use_caluma_form,
):
    url = reverse("notificationtemplate-sendmail", args=[notification_template.pk])

    requests_mock.post(
        "http://caluma:8000/graphql/",
        text=json.dumps(
            {
                "data": {
                    "allDocuments": {
                        "edges": [
                            {
                                "node": {
                                    "id": "RG9jdW1lbnQ6NjYxOGU5YmQtYjViZi00MTU2LWI0NWMtZTg0M2Y2MTFiZDI2",
                                    "meta": {
                                        "camac-instance-id": instance.pk,
                                        "ebau-number": "2019-01",
                                    },
                                    "form": {
                                        "slug": "baugesuch",
                                        "name": "Baugesuch",
                                        "meta": {"is-main-form": True},
                                    },
                                }
                            }
                        ]
                    }
                }
            }
        ),
    )

    data = {
        "data": {
            "type": "notification-template-sendmails",
            "attributes": {"recipient-types": ["applicant"]},
            "relationships": {
                "instance": {"data": {"type": "instances", "id": instance.pk}}
            },
        }
    }

    response = admin_client.post(url, data=data)

    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert len(mailoutbox) == 1

    mail = mailoutbox[0]

    assert (
        mail.subject
        == f"{settings.EMAIL_PREFIX_SUBJECT}Baugesuch 2019-01 ({instance.pk})"
    )
