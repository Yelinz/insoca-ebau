import io

import pytest
from django.urls import reverse
from PIL import Image
from pytest_factoryboy import LazyFixture
from rest_framework import status

from camac.document import models, serializers

from .data import django_file


@pytest.mark.parametrize(
    "role__name,instance__user,num_queries",
    [
        ("Applicant", LazyFixture("admin_user"), 9),
        ("Reader", LazyFixture("user"), 9),
        ("Canton", LazyFixture("user"), 9),
        ("Municipality", LazyFixture("user"), 9),
        ("Service", LazyFixture("user"), 9),
    ],
)
def test_attachment_list(
    admin_client,
    attachment_attachment_sections,
    num_queries,
    activation,
    django_assert_num_queries,
    role,
    mocker,
):
    url = reverse("attachment-list")

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {
            "demo": {
                role.name.lower(): {
                    "admin": [attachment_attachment_sections.attachmentsection_id]
                }
            }
        },
    )

    included = serializers.AttachmentSerializer.included_serializers
    with django_assert_num_queries(num_queries):
        response = admin_client.get(
            url,
            data={
                "name": attachment_attachment_sections.attachment.name.split(".")[0],
                "include": ",".join(included.keys()),
            },
        )
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["id"] == str(attachment_attachment_sections.attachment.pk)


@pytest.mark.parametrize("instance_state__name", ["nfd"])
@pytest.mark.parametrize(
    "filename,mime_type,role__name,instance__user,instance__location,activation__service,instance__group,acl_mode,status_code",
    [
        # applicant creates valid pdf attachment on a instance of its own in a
        # attachment section with admin permissions
        (
            "multiple-pages.pdf",  # filename
            "application/pdf",  # mime_type
            "Applicant",  # role__name
            LazyFixture("admin_user"),  # instance__user
            LazyFixture("location"),  # instance__location
            LazyFixture("service"),  # activation__service
            LazyFixture("group"),  # instance__group
            models.ADMIN_PERMISSION,  # attachment_section_group_acl__mode
            status.HTTP_201_CREATED,  # status_code
        ),
        # user with role Municipality creates valid jpg attachment on an
        # instance of its location in a attachment section with admin
        # permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Municipality",
            LazyFixture("user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Service creates valid jpg attachment on an
        # instance which is assigned to user in an activation in
        # an attachment section with admin permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Service",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Service creates valid jpg attachment on an
        # instance which is assigned to user in an activation in
        # an attachment section with internal admin permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Service",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMININTERNAL_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Service creates valid jpg attachment on an
        # instance which is assigned to user in an activation in
        # an attachment section with service admin permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Service",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMINSERVICE_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Canton creates valid jpg attachment on any
        # instance with attachment section with admin permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Canton",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Applicant tries to create invalid gif attachment
        # on its own instance with attachment section with admin permissions
        (
            "invalid-attachment.gif",
            "image/gif",
            "Applicant",
            LazyFixture("admin_user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # user with role Applicant tries to create valid pdf attachment
        # on instance which doesn't belong to him with attachment section
        # with admin permissions
        (
            "multiple-pages.pdf",
            "application/pdf",
            "Applicant",
            LazyFixture("user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # user with role Applicant tries to create valid jpg attachment
        # on its own instance with attachment section with only read rights
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Applicant",
            LazyFixture("admin_user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.READ_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # user with role Municipality tries to create valid jpg attachment
        # on instance of a different location with attachment section
        # with admin rights
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Municipality",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture(lambda service_factory: service_factory()),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # user with role Municipality tries to create valid jpg attachment
        # on instance of a different location but with circulation activation
        # on attachment section with admin rights
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Municipality",
            LazyFixture("user"),
            LazyFixture(lambda location_factory: location_factory()),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_201_CREATED,
        ),
        # user with role Municipality creates valid jpg attachment on an
        # instance of its location in a attachment section with admin
        # permissions but in a group user doesn't belong to
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Municipality",
            LazyFixture("user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture(lambda group_factory: group_factory()),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # user with role Service tries to create valid jpg attachment
        # on instance without activation with attachment section
        # with admin rights
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Service",
            LazyFixture("admin_user"),
            LazyFixture("location"),
            LazyFixture(lambda service_factory: service_factory()),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # reader can't create anything, not even with admin permissions
        (
            "test-thumbnail.jpg",
            "image/jpeg",
            "Reader",
            LazyFixture("admin_user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_400_BAD_REQUEST,
        ),
        # support can upload attachments
        (
            "multiple-pages.pdf",
            "application/pdf",
            "Support",
            LazyFixture("admin_user"),
            LazyFixture("location"),
            LazyFixture("service"),
            LazyFixture("group"),
            models.ADMIN_PERMISSION,
            status.HTTP_201_CREATED,
        ),
    ],
)
def test_attachment_create(
    admin_client,
    instance,
    attachment_section,
    activation,
    mime_type,
    filename,
    status_code,
    mailoutbox,
    acl_mode,
    role,
    mocker,
):
    url = reverse("attachment-list")

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {"demo": {role.name.lower(): {acl_mode: [attachment_section.pk]}}},
    )

    path = django_file(filename)
    data = {"instance": instance.pk, "path": path.file, "group": instance.group.pk}
    response = admin_client.post(url, data=data, format="multipart")
    assert response.status_code == status_code

    if status_code == status.HTTP_201_CREATED:
        json = response.json()
        attributes = json["data"]["attributes"]
        assert attributes["size"] == path.size
        assert attributes["name"] == filename
        assert attributes["mime-type"] == mime_type
        relationships = json["data"]["relationships"]
        assert relationships["attachment-sections"]["data"][0]["id"] == str(
            attachment_section.pk
        )
        assert relationships["group"]["data"]["id"] == str(instance.group.pk)

        # download uploaded attachment
        response = admin_client.get(attributes["path"])
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Disposition"] == (
            'attachment; filename="{0}"'.format(filename)
        )
        assert response["Content-Type"].startswith(mime_type)
        assert response["X-Accel-Redirect"] == "/attachments/files/%s/%s" % (
            instance.pk,
            filename,
        )

        assert len(mailoutbox) == 1


def test_attachment_download_404(admin_client, attachment):
    url = reverse("attachment-download", args=[attachment.path])
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "role__name,instance__user,instance_state__name,acl_mode",
    [("Applicant", LazyFixture("admin_user"), "new", models.ADMIN_PERMISSION)],
)
@pytest.mark.parametrize(
    "multi,expected_name", [(False, "multiple-pages.pdf"), (True, "attachments.zip")]
)
def test_attachment_download(
    admin_client,
    service,
    instance,
    attachment_factory,
    attachment_section,
    acl_mode,
    multi,
    expected_name,
    mocker,
):
    attachment1 = attachment_factory(
        instance=instance, service=service, path=django_file("multiple-pages.pdf")
    )

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {"demo": {"applicant": {acl_mode: [attachment_section.pk]}}},
    )

    test_path = "/".join(str(attachment1.path).split("/")[3:])
    attachment1.path = test_path
    attachment1.path.name = test_path
    attachment1.name = "multiple-pages.pdf"
    attachment1.save()
    attachments = [attachment1]

    attachment2 = attachment_factory(
        instance=instance, service=service, path=django_file("multiple-pages.pdf")
    )
    attachment2.path = test_path
    attachment2.path.name = test_path
    attachment2.name = "multiple-pages-2.pdf"
    attachment2.save()

    if multi:
        attachments.append(attachment2)

    attachment_section.attachments.set(attachments)

    filter = ",".join([str(a.pk) for a in attachments])

    url = f"{reverse('multi-attachment-download')}?attachments={filter}"
    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    assert (
        response._headers["content-disposition"][1]
        == f'attachment; filename="{expected_name}"'
    )


@pytest.mark.parametrize(
    "filter,status_code",
    [
        ("?attachments=", status.HTTP_400_BAD_REQUEST),
        ("?attachments=,", status.HTTP_400_BAD_REQUEST),
        ("?attachments=777", status.HTTP_404_NOT_FOUND),
        ("?attachments=somestring", status.HTTP_400_BAD_REQUEST),
        ("", status.HTTP_400_BAD_REQUEST),
    ],
)
def test_invalid_attachment_download(admin_client, filter, status_code):
    url = f"{reverse('multi-attachment-download')}{filter}"
    response = admin_client.get(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
@pytest.mark.parametrize(
    "attachment__path,status_code",
    [
        (django_file("multiple-pages.pdf"), status.HTTP_200_OK),
        (django_file("test-thumbnail.jpg"), status.HTTP_200_OK),
        (django_file("no-thumbnail.txt"), status.HTTP_404_NOT_FOUND),
    ],
)
def test_attachment_thumbnail(
    admin_client,
    attachment_attachment_sections,
    attachment_attachment_section_factory,
    attachment_section_group_acl,
    status_code,
    mocker,
):
    aasa = attachment_attachment_sections.attachment
    attachment_attachment_section_factory(attachment=aasa)
    url = reverse("attachment-thumbnail", args=[aasa.pk])

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {
            "demo": {
                "applicant": {
                    "admin": [
                        section.pk for section in models.AttachmentSection.objects.all()
                    ]
                }
            }
        },
    )

    response = admin_client.get(url)
    assert response.status_code == status_code
    if status_code == status.HTTP_200_OK:
        assert response["Content-Type"] == "image/jpeg"
        image = Image.open(io.BytesIO(response.content))
        assert image.height == 300


@pytest.mark.parametrize(
    "role__name,instance__user", [("Canton", LazyFixture("admin_user"))]
)
@pytest.mark.parametrize(
    "send_path,status_code",
    [(True, status.HTTP_400_BAD_REQUEST), (False, status.HTTP_200_OK)],
)
def test_attachment_update(
    admin_client,
    attachment_section,
    attachment_attachment_sections,
    attachment_attachment_section_factory,
    attachment_section_group_acl,
    status_code,
    send_path,
    mocker,
):
    aasa = attachment_attachment_sections.attachment
    attachment_attachment_section_factory(attachment=aasa)
    url = reverse("attachment-detail", args=[aasa.pk])
    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {
            "demo": {
                "canton": {
                    "admin": [
                        section.pk for section in models.AttachmentSection.objects.all()
                    ]
                }
            }
        },
    )

    format = ""
    data = {
        "data": {
            "type": "attachments",
            "id": aasa.pk,
            "relationships": {
                "attachment-sections": {
                    "data": [
                        {"type": "attachment-sections", "id": attachment_section.pk}
                    ]
                }
            },
        }
    }
    if send_path:
        format = "multipart"
        data = {"path": aasa.path}

    response = admin_client.patch(url, data=data, format=format)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "role__name,instance__user",
    [("Applicant", LazyFixture("admin_user")), ("Reader", LazyFixture("admin_user"))],
)
def test_attachment_detail(
    admin_client,
    attachment_attachment_sections,
    attachment_section_group_acl,
    role,
    mocker,
):
    url = reverse(
        "attachment-detail", args=[attachment_attachment_sections.attachment.pk]
    )
    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {
            "demo": {
                role.name.lower(): {
                    "admin": [attachment_attachment_sections.attachmentsection_id]
                }
            }
        },
    )

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "role__name,instance__user", [("Applicant", LazyFixture("admin_user"))]
)
@pytest.mark.parametrize(
    "instance_state__name,attachment__path,attachment__service,acl_mode,status_code",
    [
        (
            "new",
            django_file("multiple-pages.pdf"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMIN_PERMISSION,
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "new",
            django_file("test-thumbnail.jpg"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMIN_PERMISSION,
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "new",
            django_file("no-thumbnail.txt"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMIN_PERMISSION,
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "new",
            django_file("no-thumbnail.txt"),
            LazyFixture("service"),
            models.ADMININTERNAL_PERMISSION,
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "new",
            django_file("no-thumbnail.txt"),
            LazyFixture("service"),
            models.ADMINSERVICE_PERMISSION,
            status.HTTP_204_NO_CONTENT,
        ),
        (
            "new",
            django_file("test-thumbnail.jpg"),
            LazyFixture(lambda service_factory: service_factory()),
            models.WRITE_PERMISSION,
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "subm",
            django_file("test-thumbnail.jpg"),
            LazyFixture(lambda service_factory: service_factory()),
            models.WRITE_PERMISSION,
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "subm",
            django_file("test-thumbnail.jpg"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMIN_PERMISSION,
            status.HTTP_403_FORBIDDEN,
        ),
        (
            "new",
            django_file("no-thumbnail.txt"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMININTERNAL_PERMISSION,
            status.HTTP_404_NOT_FOUND,
        ),
        (
            "new",
            django_file("no-thumbnail.txt"),
            LazyFixture(lambda service_factory: service_factory()),
            models.ADMINSERVICE_PERMISSION,
            status.HTTP_403_FORBIDDEN,
        ),
    ],
)
def test_attachment_delete(
    admin_client, attachment_attachment_sections, status_code, mocker, acl_mode
):
    url = reverse(
        "attachment-detail", args=[attachment_attachment_sections.attachment.pk]
    )
    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {
            "demo": {
                "applicant": {
                    acl_mode: [
                        section.pk for section in models.AttachmentSection.objects.all()
                    ]
                }
            }
        },
    )

    response = admin_client.delete(url)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "instance_state__name,role__name,instance__user,instance__location,activation__service,instance__group,acl_mode",
    [
        (
            "nfd",
            "Applicant",  # role__name
            LazyFixture("admin_user"),  # instance__user
            LazyFixture("location"),  # instance__location
            LazyFixture("service"),  # activation__service
            LazyFixture("group"),  # instance__group
            models.ADMIN_PERMISSION,  # attachment_section_group_acl__mode
        )
    ],
)
@pytest.mark.parametrize(
    "attachment_section__allowed_mime_types,filename,status_code",
    [
        ([], "invalid-attachment.gif", status.HTTP_201_CREATED),
        (["application/pdf"], "invalid-attachment.gif", status.HTTP_400_BAD_REQUEST),
        (
            ["application/pdf", "image/jpeg"],
            "test-thumbnail.jpg",
            status.HTTP_201_CREATED,
        ),
    ],
)
def test_attachment_mime_type(
    admin_client,
    instance,
    attachment_section,
    activation,
    filename,
    status_code,
    acl_mode,
    role,
    mocker,
):
    url = reverse("attachment-list")

    # fix permissions
    mocker.patch(
        "camac.document.permissions.PERMISSIONS",
        {"demo": {role.name.lower(): {"admin": [attachment_section.pk]}}},
    )

    path = django_file(filename)
    data = {"instance": instance.pk, "path": path.file, "group": instance.group.pk}
    response = admin_client.post(url, data=data, format="multipart")
    assert response.status_code == status_code
