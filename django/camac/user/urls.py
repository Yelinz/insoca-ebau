from django.conf.urls import url
from rest_framework.routers import SimpleRouter

from . import views

r = SimpleRouter(trailing_slash=False)

r.register(r"locations", views.LocationView)
r.register(r"roles", views.RoleView)
r.register(r"services", views.ServiceView)
r.register(r"public-services", views.PublicServiceView, basename="publicservice")
r.register(r"users", views.UserView)

urlpatterns = [url(r"^me", views.MeView.as_view(), name="me")]

urlpatterns.extend(r.urls)
