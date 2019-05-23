from django.urls import reverse
from rest_framework import status

from camac.markers import only_schwyz

# module-level skip if we're not testing Schwyz variant
pytestmark = only_schwyz


def test_form_list(admin_client, form):
    url = reverse("form-list")

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK

    json = response.json()
    assert len(json["data"]) == 1
    assert json["data"][0]["id"] == str(form.pk)


def test_form_detail(admin_client, form):
    url = reverse("form-detail", args=[form.pk])

    response = admin_client.get(url)
    assert response.status_code == status.HTTP_200_OK
