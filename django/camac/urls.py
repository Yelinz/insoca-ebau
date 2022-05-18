from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import re_path
from django.utils.module_loading import import_string
from ebau_gwr.linker.views import GWRLinkViewSet
from ebau_gwr.token_proxy.views import TokenProxyView
from rest_framework.routers import SimpleRouter

from camac.caluma.views import CamacAuthenticatedGraphQLView

# TODO: Ensure that only the necessary routes are registered dependening on
# settings.APPLICATION_NAME


class UnswaggeredGWRLinkViewSet(GWRLinkViewSet):
    swagger_schema = None


class UnswaggeredTokenProxyView(TokenProxyView):
    swagger_schema = None


r = SimpleRouter(trailing_slash=False)

r.register(
    r"^api/v1/housing-stat-token",
    UnswaggeredTokenProxyView,
    basename="housingstattoken",
)
r.register(r"^api/v1/linker/gwr-links", UnswaggeredGWRLinkViewSet)

urlpatterns = [
    re_path(r"^api/v1/", include("camac.applicants.urls")),
    re_path(r"^api/v1/", include("camac.core.urls")),
    re_path(r"^api/v1/", include("camac.user.urls")),
    re_path(r"^api/v1/", include("camac.instance.urls")),
    re_path(r"^api/v1/", include("camac.document.urls")),
    re_path(r"^api/v1/", include("camac.dossier_import.urls")),
    re_path(r"^api/v1/", include("camac.circulation.urls")),
    re_path(r"^api/v1/", include("camac.notification.urls")),
    re_path(r"^api/v1/", include("camac.objection.urls")),
    re_path(r"^api/v1/", include("camac.gisbern.urls")),
    re_path(r"^api/v1/", include("camac.responsible.urls")),
    re_path(r"^api/v1/stats/", include("camac.stats.urls")),
    re_path(r"^django-admin/", admin.site.urls),
    re_path(r"^oidc/", include("mozilla_django_oidc.urls")),
    re_path(
        r"^graphql",
        CamacAuthenticatedGraphQLView.as_view(graphiql=settings.DEBUG),
        name="graphql",
    ),
    # re_path(r'^api/docs/$', schema_view),
    # re_path(r'^api/auth/$', include('keycloak_adapter.urls')),
] + r.urls


if settings.APPLICATION["ECH0211"]["API_ACTIVE"]:
    urlpatterns += (
        re_path(r"^ech/v1/", include(settings.APPLICATION["ECH0211"]["URLS"])),
    )
    try:
        SCHEMA_VIEW = import_string(
            f"{settings.APPLICATION['ECH0211']['SWAGGER_PATH']}.SCHEMA_VIEW"
        )
    except ImportError:
        SCHEMA_VIEW = None
    if SCHEMA_VIEW:
        urlpatterns += [
            re_path(
                r"^api/swagger(?P<format>\.json|\.yaml)$",
                SCHEMA_VIEW.without_ui(cache_timeout=0),
                name="schema-json",
            ),
            re_path(
                r"^api/swagger/$",
                SCHEMA_VIEW.with_ui("swagger", cache_timeout=0),
                name="schema-swagger-ui",
            ),
            re_path(
                r"^api/redoc/$",
                SCHEMA_VIEW.with_ui("redoc", cache_timeout=0),
                name="schema-redoc",
            ),
        ]

if settings.ENABLE_SILK:  # pragma: no cover
    urlpatterns.append(re_path(r"^api/silk/", include("silk.urls", namespace="silk")))
