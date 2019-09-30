import json
import os
import re
from datetime import timedelta

import environ

env = environ.Env()
ROOT_DIR = environ.Path(__file__) - 2

ENV_FILE = env.str("DJANGO_ENV_FILE", default=ROOT_DIR(".env"))
if os.path.exists(ENV_FILE):  # pragma: no cover
    environ.Env.read_env(ENV_FILE)

ENV = env.str("APPLICATION_ENV", default="production")
APPLICATION_NAME = env.str("APPLICATION")
APPLICATION_DIR = ROOT_DIR.path(APPLICATION_NAME)
FORM_CONFIG = json.loads(APPLICATION_DIR.file("form.json").read())


def default(default_dev=env.NOTSET, default_prod=env.NOTSET):
    """Environment aware default."""
    return default_prod if ENV == "production" else default_dev


SECRET_KEY = env.str("DJANGO_SECRET_KEY", default=default("uuuuuuuuuu"))
DEBUG = env.bool("DJANGO_DEBUG", default=default(True, False))
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=default(["*"]))

DEMO_MODE = env.bool("DEMO_MODE", default=False)

# Apache swallows info about HTTPS request, leading to issues with FileFields
# See https://docs.djangoproject.com/en/2.2/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.postgres",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "drf_yasg",
    "camac.core.apps.DefaultConfig",
    "camac.user.apps.DefaultConfig",
    "camac.instance.apps.DefaultConfig",
    "camac.document.apps.DefaultConfig",
    "camac.circulation.apps.DefaultConfig",
    "camac.notification.apps.DefaultConfig",
    "camac.responsible.apps.DefaultConfig",
    "camac.file.apps.DefaultConfig",
    "camac.applicants.apps.DefaultConfig",
    "camac.auditlog.apps.DefaultConfig",
    "camac.tags.apps.DefaultConfig",
    "camac.echbern",
    "sorl.thumbnail",
    "django_clamd",
    "reversion",
    "gisbern",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "camac.user.middleware.GroupMiddleware",
    "camac.middleware.LoggingMiddleware",
    "reversion.middleware.RevisionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
]


ROOT_URLCONF = "camac.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ]
        },
    }
]

WSGI_APPLICATION = "camac.wsgi.application"

# Application specific settings
# an application is defined by the customer e.g. uri, schwyz, etc.

APPLICATIONS = {
    "demo": {
        # Mapping between camac role and instance permission.
        "ROLE_PERMISSIONS": {
            # Commonly used roles
            "Applicant": "applicant",
            "Municipality": "municipality",
            "Service": "service",
            "Reader": "reader",
            "Canton": "canton",
            "PublicReader": "public_reader",
            "Support": "support",
        },
        "IS_MULTILINGUAL": False,
        "SUBMIT": {"WORKFLOW_ITEM": None},
        "NOTIFICATIONS": {"SUBMIT": None, "APPLICANT": {"NEW": None, "EXISTING": None}},
        "PUBLICATION_DURATION": timedelta(days=30),
        "FORM_BACKEND": "camac-ng",
    },
    "kt_schwyz": {
        "ROLE_PERMISSIONS": {
            "Gemeinde": "municipality",
            "Gemeinde Sachbearbeiter": "municipality",
            "Fachstelle": "service",
            "Fachstelle Sachbearbeiter": "service",
            "Kanton": "canton",
            "Lesezugriff": "reader",
            "Publikation": "public_reader",
        },
        "NOTIFICATIONS": {"SUBMIT": 16, "APPLICANT": {"NEW": 19, "EXISTING": 20}},
        "SUBMIT": {"WORKFLOW_ITEM": 10},
        "PUBLICATION_DURATION": timedelta(days=30),
        "IS_MULTILINGUAL": False,
        "FORM_BACKEND": "camac-ng",
    },
    "kt_bern": {
        "ROLE_PERMISSIONS": {
            "service-lead": "service",
            "service-clerk": "service",
            "service-readonly": "service",
            "subservice": "service",
            "municipality-lead": "municipality",
            "municipality-clerk": "municipality",
            "municipality-readonly": "municipality",
            "construction-control-lead": "municipality",
            "construction-control-clerk": "municipality",
            "construction-control-readonly": "municipality",
            "support": "support",
        },
        "NOTIFICATIONS": {
            "SUBMIT": [
                {"template_id": 1, "recipient_types": ["applicant"]},
                {"template_id": 2, "recipient_types": ["leitbehoerde"]},
            ],
            "REPORT": [
                {"template_id": 26, "recipient_types": ["applicant"]},
                {"template_id": 36, "recipient_types": ["construction_control"]},
            ],
            "FINALIZE": [
                {"template_id": 37, "recipient_types": ["construction_control"]}
            ],
            "START_CLAIM": [{"template_id": 13, "recipient_types": ["applicant"]}],
            "END_CLAIM": [{"template_id": 32, "recipient_types": ["leitbehoerde"]}],
            "APPLICANT": {"NEW": None, "EXISTING": None},
        },
        "IS_MULTILINGUAL": True,
        "FORM_BACKEND": "caluma",
        "CALUMA": {"FORM_PERMISSIONS": ["main", "sb1", "sb2", "nfd"]},
        # "DEMO_MODE_GROUPS": [20003, 20006, 20096, 20144, 20069],  # DE
        "DEMO_MODE_GROUPS": [22274, 22271, 20099, 20078],  # FR
        "ACTIVE_SERVICE_FILTERS": {"service__service_group__pk__in": [2, 20000]},
    },
    "kt_uri": {"FORM_BACKEND": "camac"},
}

APPLICATION = APPLICATIONS.get(APPLICATION_NAME, {})

PUBLIC_BASE_URL = env.str(
    "DJANGO_PUBLIC_BASE_URL", default="http://caluma-portal.local"
)

INTERNAL_BASE_URL = env.str("DJANGO_INTERNAL_BASE_URL", default="http://camac-ng.local")

PUBLIC_INSTANCE_URL_TEMPLATE = "{public_base_url}/instances/{instance_id}"
INTERNAL_INSTANCE_URL_TEMPLATE = (
    "{internal_base_url}/index/redirect-to-instance-resource/instance-id/{instance_id}"
)

# Logging

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {"django": {"handlers": ["console", "mail_admins"], "level": "INFO"}},
}

REQUEST_LOGGING_METHODS = env.list(
    "DJANGO_REQUEST_LOGGING_METHODS",
    default=default(["POST", "PUT", "PATCH", "DELETE"], []),
)
REQUEST_LOGGING_CONTENT_TYPES = env.list(
    "DJANGO_REQUEST_LOGGING_CONTENT_TYPES", default=["application/vnd.api+json"]
)

# Managing files

MEDIA_ROOT = env.str("DJANGO_MEDIA_ROOT", default=default(ROOT_DIR("media")))
ATTACHMENT_ZIP_PATH = env.str(
    "DJANGO_ATTACHMENT_ZIP_PATH", default="/tmp/camac/tmpfiles/zips/"
)

STATIC_ROOT = ROOT_DIR("staticfiles")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SWAGGER_SETTINGS = {
    "USE_SESSION_AUTH": False,
    "SECURITY_DEFINITIONS": {
        "oauth2": {
            "type": "oauth2",
            "tokenUrl": "http://camac-ng-keycloak.local/auth/realms/ebau/protocol/openid-connect/token",
            "authorizationUrl": "http://camac-ng-keycloak.local/auth/realms/ebau/protocol/openid-connect/auth",
            "flow": "application",
            "scopes": {},
        }
    },
    "DEFAULT_PAGINATOR_INSPECTORS": [
        "camac.swagger.DjangoRestJsonApiResponsePagination",
        "drf_yasg.inspectors.CoreAPICompatInspector",
    ],
    "DEFAULT_FIELD_INSPECTORS": [
        "camac.swagger.ModelSerializerInspector",
        "drf_yasg.inspectors.CamelCaseJSONFilter",
        "drf_yasg.inspectors.ReferencingSerializerInspector",
        "drf_yasg.inspectors.RelatedFieldInspector",
        "drf_yasg.inspectors.ChoiceFieldInspector",
        "drf_yasg.inspectors.FileFieldInspector",
        "drf_yasg.inspectors.DictFieldInspector",
        "drf_yasg.inspectors.HiddenFieldInspector",
        "drf_yasg.inspectors.RecursiveFieldInspector",
        "drf_yasg.inspectors.SerializerMethodFieldInspector",
        "drf_yasg.inspectors.SimpleFieldInspector",
        "drf_yasg.inspectors.StringDefaultFieldInspector",
    ],
}

DEFAULT_FILE_STORAGE = env.str(
    "DJANGO_DEFAULT_FILE_STORAGE", default="django.core.files.storage.FileSystemStorage"
)
FILE_UPLOAD_PERMISSIONS = env.int("FILE_UPLOAD_PERMISSIONS", default=0o644)

THUMBNAIL_ENGINE = "sorl.thumbnail.engines.convert_engine.Engine"

ALLOWED_DOCUMENT_MIMETYPES = env.list(
    "DJANGO_ALLOWED_DOCUMENT_MIMETYPES",
    default=["image/png", "image/jpeg", "application/pdf"],
)

# Unoconv webservice
# https://github.com/zrrrzzt/tfk-api-unoconv

UNOCONV_URL = env.str("DJANGO_UNOCONV_URL", default="http://localhost:3000")


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "camac.core.postgresql_dbdefaults",
        "NAME": env.str("DJANGO_DATABASE_NAME", default=APPLICATION_NAME),
        "USER": env.str("DJANGO_DATABASE_USER", default="camac"),
        "PASSWORD": env.str("DJANGO_DATABASE_PASSWORD", default=default("camac")),
        "HOST": env.str("DJANGO_DATABASE_HOST", default="localhost"),
        "PORT": env.str("DJANGO_DATABASE_PORT", default=""),
    }
}

# Sequence ranges to be used for each developer. Note: NEVER EVER
# EVER change this without talking to the affected developers. New
# developers should just be appended instead (which is safe).
SEQUENCE_NAMESPACES_SIZE = 10000
SEQUENCE_NAMESPACES = {}


# Cache
# https://docs.djangoproject.com/en/1.11/ref/settings/#caches

CACHES = {
    "default": {
        "BACKEND": env.str(
            "DJANGO_CACHE_BACKEND",
            default="django.core.cache.backends.memcached.MemcachedCache",
        ),
        "LOCATION": env.str("DJANGO_CACHE_LOCATION", default="127.0.0.1:11211"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LOCALE_NAME = "de_CH"
LANGUAGE_CODE = "de"
LANGUAGES = [("de", "German"), ("fr", "French")]
TIME_ZONE = "Europe/Zurich"
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (os.path.join(ROOT_DIR, "locale"),)


AUTH_PASSWORT_SALT = "ds5fsdFd763znsPO"
AUTH_USER_MODEL = "user.User"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework_json_api.pagination.JsonApiPageNumberPagination",
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework_json_api.parsers.JSONParser",
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "camac.user.permissions.IsGroupMember",
        "camac.user.permissions.ViewPermissions",
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "camac.user.authentication.JSONWebTokenKeycloakAuthentication",
    ),
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "ORDERING_PARAM": "sort",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.MultiPartRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
}

JSON_API_FORMAT_FIELD_NAMES = "dasherize"
JSON_API_FORMAT_TYPES = "dasherize"
JSON_API_PLURALIZE_TYPES = True

# Clamav service

CLAMD_USE_TCP = True
CLAMD_TCP_ADDR = env.str("DJANGO_CLAMD_TCP_ADDR", default="localhost")
CLAMD_ENABLED = env.bool("DJANGO_CLAMD_ENABLED", default=True)


# Keycloak service

KEYCLOAK_URL = env.str("KEYCLOAK_URL", default="http://camac-ng-keycloak.local/auth/")
KEYCLOAK_REALM = env.str("KEYCLOAK_REALM", default="ebau")
KEYCLOAK_CLIENT = env.str("KEYCLOAK_CLIENT", default="camac")
OIDC_BEARER_TOKEN_REVALIDATION_TIME = env.int(
    "OIDC_BEARER_TOKEN_REVALIDATION_TIME", default=120
)
REGISTRATION_URL = env.str(
    "DJANGO_REGISTRATION_URL",
    default=f"{KEYCLOAK_URL}realms/{KEYCLOAK_REALM}/login-actions/registration?client_id={KEYCLOAK_CLIENT}",
)

# Email definition

DEFAULT_FROM_EMAIL = env.str(
    "DJANGO_DEFAULT_FROM_EMAIL", default("webmaster@localhost")
)

SERVER_EMAIL = env.str("DJANGO_SERVER_EMAIL", default("root@localhost"))

EMAIL_HOST = env.str("DJANGO_EMAIL_HOST", default("localhost"))
EMAIL_PORT = env.str("DJANGO_EMAIL_PORT", 25)

EMAIL_HOST_USER = env.str("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env.str("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env.str("DJANGO_EMAIL_USE_TLS", False)

EMAIL_PREFIX_SUBJECT = env.str("EMAIL_PREFIX_SUBJECT", default("[eBau Test]: ", ""))
EMAIL_PREFIX_BODY = env.str(
    "EMAIL_PREFIX_BODY",
    default(
        (
            "Hinweis: Diese Nachricht wurde von einem Testsystem versendet.\n"
            "Es dient nur zu Testzwecken und kann ignoriert werden\n\n"
        ),
        "",
    ),
)


# Merge definition
MERGE_DATE_FORMAT = env.str("DJANGO_MERGE_DATE_FORMAT", "%d.%m.%Y")
MERGE_ANSWER_PERIOD = env.int("DJANGO_MERGE_ANSWER_PERIOD", 20)


def parse_admins(admins):
    """
    Parse env admins to django admins.

    Example of DJANGO_ADMINS environment variable:
    Test Example <test@example.com>,Test2 <test2@example.com>
    """
    result = []
    for admin in admins:
        match = re.search(r"(.+) \<(.+@.+)\>", admin)
        if not match:
            raise environ.ImproperlyConfigured(
                'In DJANGO_ADMINS admin "{0}" is not in correct '
                '"Firstname Lastname <email@example.com>"'.format(admin)
            )
        result.append((match.group(1), match.group(2)))
    return result


ADMINS = parse_admins(env.list("DJANGO_ADMINS", default=[]))

# GIS API (Kt. BE)
GIS_BASE_URL = env.str("GIS_BASE_URL", "https://www.geoservice.apps.be.ch")
GIS_API_USER = env.str("GIS_API_USER", "")
GIS_API_PASSWORD = env.str("GIS_API_PASSWORD", "")

GIS_SKIP_BOOLEAN_LAYERS = env.list("GIS_SKIP_BOOLEAN_LAYERS", default=[])

GIS_SKIP_SPECIAL_LAYERS = env.list("GIS_SKIP_SPECIAL_LAYERS", default=[])

CALUMA_URL = env.str("CALUMA_URL", "http://caluma:8000/graphql/")

ECH_API = env.bool("ECH_API", default=ENV != "production")
