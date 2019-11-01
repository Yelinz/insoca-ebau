import pytest


@pytest.fixture
def ech_instance(db, admin_user, instance_service_factory):
    inst_serv = instance_service_factory(
        instance__user=admin_user,
        service__name="Leitbehörde Burgdorf",
        service__city="Burgdorf",
        service__zip="3400",
        service__address="Teststrasse 23",
        active=1,
    )
    return inst_serv.instance
