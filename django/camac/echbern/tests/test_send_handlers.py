import pytest
from caluma.caluma_form.models import Document, Form

from camac.constants.kt_bern import (
    ATTACHMENT_SECTION_ALLE_BETEILIGTEN,
    ATTACHMENT_SECTION_BETEILIGTE_BEHOERDEN,
    INSTANCE_STATE_DOSSIERPRUEFUNG,
    INSTANCE_STATE_EBAU_NUMMER_VERGEBEN,
    INSTANCE_STATE_FINISHED,
    INSTANCE_STATE_KOORDINATION,
    INSTANCE_STATE_REJECTED,
    INSTANCE_STATE_SB1,
    INSTANCE_STATE_TO_BE_FINISHED,
    INSTANCE_STATE_VERFAHRENSPROGRAMM_INIT,
    INSTANCE_STATE_ZIRKULATION,
    NOTICE_TYPE_NEBENBESTIMMUNG,
    NOTICE_TYPE_STELLUNGNAHME,
    NOTIFICATION_ECH,
)
from camac.core.models import (
    Activation,
    Circulation,
    DocxDecision,
    InstanceService,
    Notice,
)
from camac.echbern.tests.utils import xml_data
from camac.instance.models import Instance

from ..models import Message
from ..schema.ech_0211_2_0 import CreateFromDocument
from ..send_handlers import (
    AccompanyingReportSendHandler,
    ChangeResponsibilitySendHandler,
    CloseArchiveDossierSendHandler,
    NoticeKindOfProceedingsSendHandler,
    NoticeRulingSendHandler,
    SendHandlerException,
    TaskSendHandler,
    resolve_send_handler,
)


@pytest.mark.parametrize(
    "xml_file,expected_send_handler",
    [
        ("accompanying_report", AccompanyingReportSendHandler),
        ("change_responsibility", ChangeResponsibilitySendHandler),
        ("close_dossier", CloseArchiveDossierSendHandler),
        ("notice_ruling", NoticeRulingSendHandler),
        ("task", TaskSendHandler),
        ("kind_of_proceedings", NoticeKindOfProceedingsSendHandler),
        ("accompanying_report", None),
    ],
)
def test_resolve_send_handler(xml_file, expected_send_handler):
    data = CreateFromDocument(xml_data(xml_file))
    if not expected_send_handler:
        data.eventAccompanyingReport = None
        with pytest.raises(SendHandlerException):
            resolve_send_handler(data)
    else:
        assert resolve_send_handler(data) == expected_send_handler


@pytest.mark.parametrize(
    "judgement,instance_state_pk,has_permission,expected_state_pk",
    [
        (4, INSTANCE_STATE_DOSSIERPRUEFUNG, True, INSTANCE_STATE_REJECTED),
        (3, INSTANCE_STATE_DOSSIERPRUEFUNG, False, None),
        (1, INSTANCE_STATE_KOORDINATION, True, INSTANCE_STATE_SB1),
        (4, INSTANCE_STATE_EBAU_NUMMER_VERGEBEN, False, None),
    ],
)
def test_notice_ruling_send_handler(
    judgement,
    instance_state_pk,
    has_permission,
    expected_state_pk,
    admin_user,
    ech_instance,
    instance_state_factory,
    attachment_factory,
    attachment_section_factory,
):
    attachment_section_beteiligte_behoerden = attachment_section_factory(
        pk=ATTACHMENT_SECTION_BETEILIGTE_BEHOERDEN
    )
    attachment_section_factory(pk=ATTACHMENT_SECTION_ALLE_BETEILIGTEN)
    attachment = attachment_factory(
        uuid="00000000-0000-0000-0000-000000000000",
        name="myFile.pdf",
        instance=ech_instance,
    )
    attachment.attachment_sections.add(attachment_section_beteiligte_behoerden)

    form = Form.objects.create(slug="baugesuch", meta={"is-main-form": True})
    Document.objects.create(form=form, meta={"camac-instance-id": ech_instance.pk})

    data = CreateFromDocument(xml_data("notice_ruling"))

    data.eventNotice.decisionRuling.judgement = judgement

    state = instance_state_factory(pk=instance_state_pk)
    ech_instance.instance_state = state
    ech_instance.save()

    group = admin_user.groups.first()
    group.service = ech_instance.services.first()
    group.save()

    handler = NoticeRulingSendHandler(
        data=data,
        queryset=Instance.objects,
        user=admin_user,
        group=admin_user.groups.first(),
        auth_header=None,
    )
    assert handler.has_permission()[0] == has_permission

    if has_permission:
        expected_state = instance_state_factory(pk=expected_state_pk)
        handler.apply()
        ech_instance.refresh_from_db()
        assert ech_instance.instance_state == expected_state
        assert DocxDecision.objects.get(instance=ech_instance.pk)
        assert Message.objects.count() == 1
        assert Message.objects.first().receiver == group.service
        attachment.refresh_from_db()
        assert attachment.attachment_sections.get(
            pk=ATTACHMENT_SECTION_ALLE_BETEILIGTEN
        )


@pytest.mark.parametrize("fail", [False, True])
def test_change_responsibility_send_handler(
    fail, admin_user, service_factory, ech_instance
):
    burgdorf = ech_instance.active_service

    group = admin_user.groups.first()
    group.service = ech_instance.services.first()
    group.save()

    if not fail:
        madiswil = service_factory(pk=20351, name="Madiswil")

    data = CreateFromDocument(xml_data("change_responsibility"))

    handler = ChangeResponsibilitySendHandler(
        data=data,
        queryset=Instance.objects,
        user=admin_user,
        group=group,
        auth_header=None,
    )
    assert handler.has_permission()[0] is True

    if not fail:
        handler.apply()
        assert ech_instance.active_service == madiswil
        assert InstanceService.objects.get(
            instance=ech_instance, service=burgdorf, active=0
        )
        assert InstanceService.objects.get(
            instance=ech_instance, service=madiswil, active=1
        )
        assert Message.objects.count() == 1
        assert Message.objects.first().receiver == madiswil
    else:
        with pytest.raises(SendHandlerException):
            handler.apply()


@pytest.mark.parametrize(
    "requesting_service,state_pk,success",
    [
        ("leitbehörde", INSTANCE_STATE_TO_BE_FINISHED, True),
        ("baukontrolle", INSTANCE_STATE_TO_BE_FINISHED, True),
        ("leitbehörde", INSTANCE_STATE_KOORDINATION, False),
        ("nobody", INSTANCE_STATE_TO_BE_FINISHED, False),
    ],
)
def test_close_dossier_send_handler(
    requesting_service,
    state_pk,
    success,
    ech_instance,
    admin_user,
    instance_service_factory,
    instance_state_factory,
):
    instance_state_factory(pk=INSTANCE_STATE_FINISHED)

    inst_serv = instance_service_factory(
        instance=ech_instance, service__name="Baukontrolle Burgdorf", active=1
    )

    ech_instance.instance_state = instance_state_factory(pk=state_pk)
    ech_instance.save()

    group = admin_user.groups.first()

    if requesting_service == "leitbehörde":
        group.service = ech_instance.services.first()
    elif requesting_service == "baukontrolle":
        group.service = inst_serv.service

    group.save()

    data = CreateFromDocument(xml_data("close_dossier"))

    handler = CloseArchiveDossierSendHandler(
        data=data,
        queryset=Instance.objects,
        user=admin_user,
        group=group,
        auth_header=None,
    )

    assert handler.has_permission()[0] is success

    if success:
        handler.apply()
        ech_instance.refresh_from_db()

        assert ech_instance.instance_state.pk == INSTANCE_STATE_FINISHED
        assert Message.objects.count() == 1
        assert Message.objects.first().receiver == ech_instance.active_service


@pytest.mark.parametrize(
    "has_circulation,has_service,valid_service_id,has_template,success",
    [
        (True, True, True, True, True),
        (False, True, True, True, True),
        (True, False, True, True, False),
        (True, True, False, True, False),
        (True, True, True, False, False),
    ],
)
def test_task_send_handler(
    has_circulation,
    has_service,
    valid_service_id,
    has_template,
    success,
    admin_user,
    circulation_factory,
    ech_instance,
    instance_state_factory,
    service_factory,
    circulation_state_factory,
    instance_resource_factory,
    notification_template_factory,
    mailoutbox,
):
    if has_template:
        notification_template_factory(slug=NOTIFICATION_ECH)

    instance_resource_factory(pk=INSTANCE_STATE_ZIRKULATION)
    circulation_state_factory(pk=1, name="RUN")
    state = instance_state_factory(pk=INSTANCE_STATE_ZIRKULATION)
    ech_instance.instance_state = state
    ech_instance.save()

    group = admin_user.groups.first()
    group.service = ech_instance.services.first()
    group.save()

    if has_service:
        service = service_factory(pk=23, email="s1@example.com")

    if has_circulation:
        circulation_factory(instance=ech_instance)  # dummy
        circulation = circulation_factory(instance=ech_instance)

    xml = xml_data("task")
    if not valid_service_id:
        xml = xml.replace("<serviceId>23</serviceId>", "<serviceId>string</serviceId>")

    data = CreateFromDocument(xml)

    handler = TaskSendHandler(
        data=data,
        queryset=Instance.objects,
        user=admin_user,
        group=group,
        auth_header="Bearer: some token",
    )
    assert handler.has_permission()[0] is True

    if success:
        handler.apply()
        assert Message.objects.count() == 1
        message = Message.objects.first()
        assert message.receiver == service
        assert Activation.objects.count() == 1
        activation = Activation.objects.first()
        assert activation.service == service
        if has_circulation:
            assert activation.circulation == circulation

        assert len(mailoutbox) == 1

        assert activation.ech_msg_created is True
        assert "s1@example.com" in mailoutbox[0].to

    else:
        with pytest.raises(SendHandlerException):
            handler.apply()


def test_task_send_handler_no_permission(admin_user, ech_instance):
    group = admin_user.groups.first()
    group.service = ech_instance.services.first()
    group.save()

    data = CreateFromDocument(xml_data("task"))

    handler = TaskSendHandler(
        data=data, queryset=Instance.objects, user=None, group=group, auth_header=None
    )
    assert handler.has_permission()[0] is False


@pytest.mark.parametrize("has_permission", [True, False])
def test_notice_kind_of_proceedings_send_handler(
    has_permission,
    attachment_section_factory,
    attachment_factory,
    admin_user,
    ech_instance,
    instance_state_factory,
    instance_resource_factory,
):
    attachment_section_beteiligte_behoerden = attachment_section_factory(
        pk=ATTACHMENT_SECTION_BETEILIGTE_BEHOERDEN
    )
    attachment_section_factory(pk=ATTACHMENT_SECTION_ALLE_BETEILIGTEN)
    attachment = attachment_factory(
        uuid="00000000-0000-0000-0000-000000000000",
        name="myFile.pdf",
        instance=ech_instance,
    )
    attachment.attachment_sections.add(attachment_section_beteiligte_behoerden)

    group = admin_user.groups.first()
    group.service = ech_instance.services.first()
    group.save()

    state = instance_state_factory(pk=INSTANCE_STATE_DOSSIERPRUEFUNG)
    if has_permission:
        state = instance_state_factory(pk=INSTANCE_STATE_VERFAHRENSPROGRAMM_INIT)
    ech_instance.instance_state = state
    ech_instance.save()

    instance_state_factory(pk=INSTANCE_STATE_ZIRKULATION)
    instance_resource_factory(pk=INSTANCE_STATE_ZIRKULATION)

    data = CreateFromDocument(xml_data("kind_of_proceedings"))

    handler = NoticeKindOfProceedingsSendHandler(
        data=data,
        queryset=Instance.objects,
        user=admin_user,
        group=group,
        auth_header=None,
    )
    assert handler.has_permission()[0] is has_permission

    if has_permission:
        handler.apply()
        assert Circulation.objects.count() == 1
        ech_instance.refresh_from_db()
        assert ech_instance.instance_state.pk == INSTANCE_STATE_ZIRKULATION

        assert Message.objects.count() == 1
        message = Message.objects.first()
        assert message.receiver == ech_instance.active_service

        attachment.refresh_from_db()
        assert attachment.attachment_sections.get(
            pk=ATTACHMENT_SECTION_ALLE_BETEILIGTEN
        )


@pytest.mark.parametrize("has_attachment", [True, False])
@pytest.mark.parametrize("has_activation", [True, False])
def test_accompanying_report_send_handler(
    has_attachment,
    has_activation,
    admin_user,
    ech_instance,
    attachment_factory,
    attachment_section_factory,
    circulation_state_factory,
    instance_state_factory,
    activation_factory,
    user_group_factory,
    notice_type_factory,
):
    user_group = user_group_factory(default_group=1)

    notice_type_factory(pk=NOTICE_TYPE_STELLUNGNAHME)
    notice_type_factory(pk=NOTICE_TYPE_NEBENBESTIMMUNG)

    if has_activation:
        activation_factory(
            circulation__instance=ech_instance,
            circulation_state=circulation_state_factory(pk=1, name="RUN"),
            service=user_group.group.service,
            user=user_group.user,
            circulation_answer=None,
        )

    done_state = circulation_state_factory(pk=2, name="DONE")

    support_group = admin_user.groups.first()
    support_group.service = ech_instance.services.first()
    support_group.save()

    state = instance_state_factory(pk=INSTANCE_STATE_ZIRKULATION)
    ech_instance.instance_state = state
    ech_instance.save()

    if has_attachment:
        attachment = attachment_factory(
            name="MyFile.pdf", uuid="00000000-0000-0000-0000-000000000000"
        )
        attachment.attachment_sections.add(attachment_section_factory(pk=7))

    data = CreateFromDocument(xml_data("accompanying_report"))

    handler = AccompanyingReportSendHandler(
        data=data,
        queryset=Instance.objects,
        user=user_group.user,
        group=user_group.group,
        auth_header=None,
    )
    if not has_activation:
        assert handler.has_permission()[0] is False
        return

    assert handler.has_permission()[0] is True

    if has_attachment:
        handler.apply()

        assert Message.objects.count() == 1
        message = Message.objects.first()
        assert message.receiver == support_group.service
        assert Activation.objects.count() == 1
        activation = Activation.objects.first()
        assert activation.circulation_state == done_state
        assert Notice.objects.count() == 2

    else:
        with pytest.raises(SendHandlerException):
            handler.apply()
