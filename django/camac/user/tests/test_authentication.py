import pytest
from django.conf import settings
from django.core.cache import cache
from jose.exceptions import ExpiredSignatureError, JOSEError
from rest_framework.exceptions import AuthenticationFailed

from camac.user.authentication import JSONWebTokenKeycloakAuthentication


@pytest.fixture(scope="function", autouse=True)
def clear_cache():
    cache.clear()


def test_authenticate_no_headers(rf):
    request = rf.request()
    assert JSONWebTokenKeycloakAuthentication().authenticate(request) is None


def test_authenticate_disabled_user(rf, admin_user, mocker):
    decode_token = mocker.patch("keycloak.KeycloakOpenID.decode_token")
    decode_token.return_value = {
        "sub": admin_user.username,
        "email": admin_user.email,
        "family_name": admin_user.name,
        "given_name": admin_user.surname,
    }
    mocker.patch("keycloak.KeycloakOpenID.certs")
    admin_user.disabled = True
    admin_user.save()

    request = rf.request(HTTP_AUTHORIZATION="Bearer some_token")
    with pytest.raises(AuthenticationFailed):
        JSONWebTokenKeycloakAuthentication().authenticate(request)


@pytest.mark.parametrize("demo_mode", [True, False])
def test_authenticate_new_user(rf, admin_user, mocker, demo_mode):
    if demo_mode:
        admin_group = admin_user.groups.first()
        inexistent_group = 2138242342
        settings.DEMO_MODE = True
        settings.APPLICATION["DEMO_MODE_GROUPS"] = [admin_group.pk, inexistent_group]
    else:
        settings.DEMO_MODE = False

    username = "new-here"

    decode_token = mocker.patch("keycloak.KeycloakOpenID.decode_token")
    decode_token.return_value = {
        "sub": username,
        "email": "new-guy@example.com",
        "family_name": "New",
        "given_name": "Guy",
    }
    mocker.patch("keycloak.KeycloakOpenID.certs")

    request = rf.request(HTTP_AUTHORIZATION="Bearer some_token")
    user, token = JSONWebTokenKeycloakAuthentication().authenticate(request)

    assert user.username == username
    if demo_mode:
        assert user.groups.count() == 1
        assert user.groups.first() == admin_group
    else:
        assert user.groups.count() == 0
    assert decode_token.return_value == token


def test_authenticate_ok(rf, admin_user, mocker):
    decode_token = mocker.patch("keycloak.KeycloakOpenID.decode_token")
    decode_token.return_value = {
        "sub": admin_user.username,
        "email": admin_user.email,
        "family_name": admin_user.name,
        "given_name": admin_user.surname,
    }
    mocker.patch("keycloak.KeycloakOpenID.certs")

    request = rf.request(HTTP_AUTHORIZATION="Bearer some_token")
    user, token = JSONWebTokenKeycloakAuthentication().authenticate(request)

    assert user == admin_user
    assert decode_token.return_value == token


@pytest.mark.parametrize("side_effect", [ExpiredSignatureError(), JOSEError()])
def test_authenticate_side_effect(rf, mocker, side_effect):
    decode_token = mocker.patch("keycloak.KeycloakOpenID.decode_token")
    decode_token.side_effect = side_effect
    mocker.patch("keycloak.KeycloakOpenID.certs")

    request = rf.request(HTTP_AUTHORIZATION="Bearer some_token")
    with pytest.raises(AuthenticationFailed):
        JSONWebTokenKeycloakAuthentication().authenticate(request)


@pytest.mark.parametrize("authorization", ["Bearer", "Bearer token token"])
def test_get_jwt_value_invalid_authorization(rf, authorization):
    request = rf.request(HTTP_AUTHORIZATION=authorization)
    with pytest.raises(AuthenticationFailed):
        JSONWebTokenKeycloakAuthentication().get_jwt_value(request)


def test_authenticate_header(rf):
    request = rf.request()
    header = JSONWebTokenKeycloakAuthentication().authenticate_header(request)
    assert settings.KEYCLOAK_REALM in header
