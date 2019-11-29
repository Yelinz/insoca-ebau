"""Helpers for exporting instance data to eCH-0211."""


import logging

import pyxb
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from pyxb import IncompleteElementContentError, UnprocessedElementContentError

from camac import camac_metadata
from camac.constants.kt_bern import (
    CIRCULATION_ANSWER_NACHFORDERUNG,
    CIRCULATION_ANSWER_NEGATIV,
    CIRCULATION_ANSWER_NICHT_BETROFFEN,
    CIRCULATION_ANSWER_POSITIV,
    DECISIONS_BEWILLIGT,
)
from camac.core.models import Answer, DocxDecision, InstanceService
from camac.instance.models import Instance

from .schema import (
    ech_0007_6_0,
    ech_0010_6_0 as ns_address,
    ech_0044_4_1,
    ech_0058_5_0,
    ech_0097_2_0 as ns_company_identification,
    ech_0129_5_0 as ns_objektwesen,
    ech_0147_t0_1 as ns_document,
    ech_0211_2_0 as ns_application,
)

logger = logging.getLogger(__name__)


def list_to_string(data, key, delimiter=", "):
    if key in data:
        return delimiter.join(data[key])


def handle_ja_nein_bool(value):
    if value in ["Ja", "ja"]:  # pragma: todo cover
        return True
    elif value in ["Nein", "nein"]:
        return False


def authority(service):
    return ns_company_identification.organisationIdentificationType(
        uid=ns_company_identification.uidStructureType(
            # We don't bother with UIDs
            uidOrganisationIdCategorie="CHE",
            uidOrganisationId="123123123",
        ),
        localOrganisationId=ns_company_identification.namedOrganisationIdType(
            organisationIdCategory="CHE", organisationId="123123123"
        ),
        organisationName=service.get_name(),
        legalForm="0223",
    )


def get_ebau_nr(instance):
    ebau_answer = Answer.objects.filter(
        question__trans__name="eBau-Nummer", instance=instance
    ).first()
    if ebau_answer:
        return ebau_answer.answer


def get_related_instances(instance, ebau_nr=None):
    ebau_nr = ebau_nr if ebau_nr else get_ebau_nr(instance)
    related_instances = []
    if ebau_nr:
        instance_pks = (
            Answer.objects.filter(question__trans__name="eBau-Nummer", answer=ebau_nr)
            .exclude(instance__pk=instance.pk)
            .select_related("instance")
            .values_list("instance", flat=True)
        )
        related_instances = Instance.objects.filter(pk__in=instance_pks)
    return related_instances


def get_document_sections(attachment):
    sections = [s.get_name() for s in attachment.attachment_sections.all()]
    return "; ".join(sections)


def get_plz(value):
    if not value or not len(str(value)) == 4:
        # use 9999 for non swiss zips
        return 9999
    return value


def get_cost(value):
    if value and value < 1000:
        return 1000
    return value


def get_keywords(attachment):
    tags = attachment.context.get("tags")
    if tags:
        return pyxb.BIND(keyword=tags)


def get_documents(attachments):
    documents = [
        ns_document.documentType(
            uuid=str(attachment.uuid),
            titles=pyxb.BIND(title=[attachment.name]),
            status="signed",  # ech0039 documentStatusType
            documentKind=get_document_sections(attachment),
            keywords=get_keywords(attachment),
            files=ns_document.filesType(
                file=[
                    ns_document.fileType(
                        pathFileName=f"{settings.INTERNAL_BASE_URL}{reverse('multi-attachment-download')}?attachments={attachment.pk}",
                        mimeType=attachment.mime_type,
                        # internalSortOrder minOccurs=0
                        # version minOccurs=0
                        # hashCode minOccurs=0
                        # hashCodeAlgorithm minOccurs=0
                    )
                ]
            ),
        )
        for attachment in attachments
    ]
    if not documents:
        documents = [
            ns_document.documentType(
                uuid="00000000-0000-0000-0000-000000000000",
                titles=pyxb.BIND(title=["dummy"]),
                status="signed",
                files=ns_document.filesType(
                    file=[
                        ns_document.fileType(pathFileName="unknown", mimeType="unknown")
                    ]
                ),
            )
        ]
    return documents


def get_realestateinformation(answers):
    re_info = [
        ns_application.realestateInformationType(
            realestate=ns_objektwesen.realestateType(
                realestateIdentification=ns_objektwesen.realestateIdentificationType(
                    EGRID=parzelle.get("e-grid-nr"),
                    number=parzelle["parzellennummer"],
                    # numberSuffix minOccurs=0
                    # subDistrict minOccurs=0
                    # lot minOccurs=0
                ),
                # authority minOccurs=0
                # date minOccurs=0
                realestateType="8",  # mapping?
                # cantonalSubKind minOccurs=0
                # status minOccurs=0
                # mutnumber minOccurs=0
                # identDN minOccurs 0
                # squareMeasure minOccurs 0
                # realestateIncomplete minOccurs 0
                coordinates=ns_objektwesen.coordinatesType(
                    LV95=pyxb.BIND(
                        east=parzelle["lagekoordinaten-ost"],
                        north=parzelle["lagekoordinaten-nord"],
                        originOfCoordinates=904,
                    )
                )
                if all(
                    k in parzelle
                    for k in ("lagekoordinaten-ost", "lagekoordinaten-nord")
                )
                else None
                # namedMetaData minOccurs 0
            ),
            municipality=ech_0007_6_0.swissMunicipalityType(
                # municipalityId minOccurs 0
                municipalityName=answers["gemeinde"],
                cantonAbbreviation="BE",
            ),
            buildingInformation=[
                ns_application.buildingInformationType(
                    building=ns_objektwesen.buildingType(
                        EGID=answers.get("gwr-egid"),
                        numberOfFloors=answers.get("effektive-geschosszahl"),
                        civilDefenseShelter=handle_ja_nein_bool(
                            answers.get("sammelschutzraum")
                        ),
                        buildingCategory=1040,  # TODO: map category to GWR categories
                        # We don't want to map the heatings, hence omitting
                        # heating=[
                        #     ns_person.heatingType(
                        #         heatGeneratorHeating=7410,
                        #         energySourceHeating=7511,
                        #     )
                        #     for heating in answers.get("feuerungsanlagen", [])[:2]
                        # ],  # eCH only accepts 2 heatingTypes
                    )
                )
            ],
            # placeName  minOccurs=0
            owner=[
                pyxb.BIND(
                    # ownerIdentification minOccurs=0
                    ownerAdress=ns_address.mailAddressType(
                        person=ns_address.personMailAddressInfoType(
                            # mrMrs="1",  # mapping?
                            # title="Dr Med",
                            firstName=owner["vorname-gesuchstellerin"],
                            lastName=owner["name-gesuchstellerin"],
                        ),
                        addressInformation=ns_address.addressInformationType(
                            # not the same as swissAddressInformationType (obv..)
                            # addressLine1 minOccurs=0
                            # addressLine2 minOccurs=0
                            # (street, houseNumber, dwellingNumber) minOccurs=0
                            # (postOfficeBoxNumber, postOfficeBoxText) minOccurs=0
                            # locality minOccurs=0
                            street=owner.get("strasse-gesuchstellerin"),
                            houseNumber=owner.get("nummer-gesuchstellerin"),
                            town=ns_address.townType(owner["ort-gesuchstellerin"]),
                            swissZipCode=get_plz(owner["plz-gesuchstellerin"]),
                            # foreignZipCode minOccurs=0
                            country="CH",
                        ),
                    )
                )
                for owner in answers.get("personalien-gesuchstellerin", [])
            ],
        )
        for parzelle in answers.get("parzelle", [])
    ]

    if not re_info:
        # happens if form == vorabklaerung
        re_info = [
            ns_application.realestateInformationType(
                realestate=ns_objektwesen.realestateType(
                    realestateIdentification=ns_objektwesen.realestateIdentificationType(
                        number=answers.get("parzellennummer", "0")
                    ),
                    realestateType="8",
                ),
                municipality=ech_0007_6_0.swissMunicipalityType(
                    municipalityName=answers.get(
                        "ort-gesuchstellerin", answers["gemeinde"]
                    ),
                    cantonAbbreviation="BE",
                ),
                buildingInformation=[
                    ns_application.buildingInformationType(
                        building=ns_objektwesen.buildingType(
                            buildingCategory=1040  # TODO: map category to GWR categories
                        )
                    )
                ],
                owner=[
                    pyxb.BIND(
                        ownerAdress=ns_address.mailAddressType(
                            person=ns_address.personMailAddressInfoType(
                                firstName=owner["vorname-gesuchstellerin"],
                                lastName=owner["name-gesuchstellerin"],
                            ),
                            addressInformation=ns_address.addressInformationType(
                                street=owner.get("strasse-gesuchstellerin"),
                                houseNumber=owner.get("nummer-gesuchstellerin"),
                                town=ns_address.townType(owner["ort-gesuchstellerin"]),
                                swissZipCode=get_plz(owner["plz-gesuchstellerin"]),
                                country="CH",
                            ),
                        )
                    )
                    for owner in answers.get("personalien-gesuchstellerin", [])
                ]
                if "personalien-gesuchstellerin" in answers
                else [
                    pyxb.BIND(
                        ownerAdress=ns_address.mailAddressType(
                            person=ns_address.personMailAddressInfoType(
                                firstName=answers[
                                    "vorname-gesuchstellerin-vorabklaerung"
                                ],
                                lastName=answers["name-gesuchstellerin-vorabklaerung"],
                            ),
                            addressInformation=ns_address.addressInformationType(
                                street=answers.get("strasse-gesuchstellerin"),
                                houseNumber=answers.get("nummer-gesuchstellerin"),
                                town=ns_address.townType(
                                    answers["ort-gesuchstellerin"]
                                ),
                                swissZipCode=get_plz(answers["plz-gesuchstellerin"]),
                                country="CH",
                            ),
                        )
                    )
                ],
            )
        ]

    return re_info


def application(instance: Instance, answers: dict):
    nature_risk = []
    if "beschreibung-der-prozessart-tabelle" in answers:
        nature_risk = [
            ns_application.natureRiskType(
                riskDesignation=row["prozessart"], riskExists=True
            )
            for row in answers["beschreibung-der-prozessart-tabelle"]
        ]

    ebau_nr = get_ebau_nr(instance)
    related_instances = get_related_instances(instance, ebau_nr)

    return ns_application.planningPermissionApplicationType(
        description=answers.get(
            "beschreibung-bauvorhaben",
            answers.get("anfrage-zur-vorabklaerung", "unknown"),
        ),
        applicationType=answers["ech-subject"],
        remark=[answers["bemerkungen"]] if "bemerkungen" in answers else [],
        # proceedingType minOccurs=0
        # profilingYesNo minOccurs=0
        # profilingDate minOccurs=0
        intendedPurpose=list_to_string(answers, "nutzungsart"),
        parkingLotsYesNo=answers.get("anzahl-abstellplaetze-fur-motorfahrzeuge", 0) > 0,
        natureRisk=nature_risk,
        constructionCost=get_cost(answers.get("baukosten-in-chf")),
        # publication minOccurs=0
        namedMetaData=[
            ns_objektwesen.namedMetaDataType(
                metaDataName="status", metaDataValue=instance.instance_state.name
            )
        ],
        locationAddress=ns_address.swissAddressInformationType(
            # addressLine1 minOccurs=0
            # addressLine2 minOccurs=0
            houseNumber=answers.get("nr", "0"),
            street=answers.get("strasse-flurname", "unknown"),
            town=answers.get("ort-grundstueck", "unknown"),
            swissZipCode=get_plz(answers.get("plz")),
            country="CH",
        ),
        realestateInformation=get_realestateinformation(answers),
        zone=[
            ns_application.zoneType(
                zoneDesignation=answers["nutzungszone"][:255].strip()
            )
        ]  # eCH allows for max 225 chars
        if "nutzungszone" in answers
        else [],
        constructionProjectInformation=ns_application.constructionProjectInformationType(
            constructionProject=ns_objektwesen.constructionProject(
                status=6701,  # we always send this. The real status is in namedMetaData
                description=answers.get("beschreibung-bauvorhaben", "unknown"),
                projectStartDate=answers.get("geplanter-baustart"),
                durationOfConstructionPhase=answers.get("dauer-in-monaten"),
                totalCostsOfProject=get_cost(answers.get("baukosten-in-chf")),
            ),
            municipality=ech_0007_6_0.swissMunicipalityType(
                municipalityName=answers["parzelle"][0].get(
                    "ort-parzelle", answers["gemeinde"]
                ),
                cantonAbbreviation="BE",
            )
            if "parzelle" in answers
            else None,
        ),
        # directive  minOccurs=0
        decisionRuling=[
            ns_application.decisionRulingType(
                judgement=1 if decision.decision == DECISIONS_BEWILLIGT else 4,
                date=decision.decision_date,
                ruling=decision.decision_type,
                rulingAuthority=authority(instance.active_service),
            )
            for decision in DocxDecision.objects.filter(instance=instance.pk)
        ],
        document=get_documents(instance.attachments.all()),
        referencedPlanningPermissionApplication=[
            permission_application_identification(i) for i in related_instances
        ],
        planningPermissionApplicationIdentification=permission_application_identification(
            instance
        ),
    )


def office(service):
    return ns_application.entryOfficeType(
        entryOfficeIdentification=authority(service),
        municipality=ech_0007_6_0.swissMunicipalityType(
            # municipalityId minOccurs 0
            municipalityName=service.get_trans_attr("city") or "unknown",
            cantonAbbreviation="BE",
        ),
    )


def permission_application_identification(instance: Instance):
    return ns_application.planningPermissionApplicationIdentificationType(
        localID=[
            ns_objektwesen.namedIdType(
                IdCategory="instanceID", Id=str(instance.instance_id)
            )
        ],
        otherID=[
            ns_objektwesen.namedIdType(
                IdCategory="instanceID", Id=str(instance.instance_id)
            )
        ],
        dossierIdentification=get_ebau_nr(instance) or "unknown",
    )


def status_notification(instance: Instance):
    return ns_application.eventStatusNotificationType(
        eventType="status notification",
        planningPermissionApplicationIdentification=permission_application_identification(
            instance
        ),
        status="in progress",  # real status is in remark
        remark=[str(instance.instance_state.get_name())],
    )


def base_delivery(instance: Instance, answers: dict):

    return ns_application.eventBaseDeliveryType(
        planningPermissionApplicationInformation=[
            (
                pyxb.BIND(
                    planningPermissionApplication=application(instance, answers),
                    relationshipToPerson=[
                        ns_application.relationshipToPersonType(
                            role="applicant", person=requestor(instance)
                        )
                    ],
                    decisionAuthority=decision_authority(instance.active_service),
                    entryOffice=office(instance.active_service),
                )
            )
        ]
    )


def submit(instance: Instance, answers: dict, event_type: str):
    return ns_application.eventSubmitPlanningPermissionApplicationType(
        eventType=ns_application.eventTypeType(event_type),
        planningPermissionApplication=application(instance, answers),
        relationshipToPerson=[
            ns_application.relationshipToPersonType(
                role="applicant", person=requestor(instance)
            )
        ],
    )


def request(instance: Instance, event_type: str):
    return ns_application.eventRequestType(
        eventType=ns_application.eventTypeType(event_type),
        planningPermissionApplicationIdentification=permission_application_identification(
            instance
        ),
    )


def accompanying_report(
    instance: Instance,
    event_type: str,
    attachments,
    circulation_answer,
    stellungnahme,
    nebenbestimmung,
):
    judgement_mapping = {
        CIRCULATION_ANSWER_POSITIV: 1,
        CIRCULATION_ANSWER_NEGATIV: 4,
        CIRCULATION_ANSWER_NICHT_BETROFFEN: 1,
        CIRCULATION_ANSWER_NACHFORDERUNG: 4,
    }

    return ns_application.eventAccompanyingReportType(
        eventType=ns_application.eventTypeType(event_type),
        planningPermissionApplicationIdentification=permission_application_identification(
            instance
        ),
        document=get_documents(attachments),
        remark=[stellungnahme] if stellungnahme else [],
        ancillaryClauses=[nebenbestimmung] if nebenbestimmung else [],
        judgement=judgement_mapping[circulation_answer.pk]
        if circulation_answer
        else None,
    )


def change_responsibility(instance: Instance):
    prev_service = (
        InstanceService.objects.filter(
            active=0,
            instance=instance,
            **settings.APPLICATION.get("ACTIVE_SERVICE_FILTERS", {}),
        )
        .first()
        .service
    )
    return ns_application.eventChangeResponsibilityType(
        eventType=ns_application.eventTypeType("change responsibility"),
        planningPermissionApplicationIdentification=permission_application_identification(
            instance
        ),
        entryOffice=office(prev_service),
        responsibleDecisionAuthority=decision_authority(instance.active_service),
    )


def delivery(
    instance: Instance,
    answers: dict,
    message_date=None,
    message_id=None,
    url=None,
    **args,
):
    """
    Generate delivery XML.

    General calling convention:
    >>> delivery(instance, answers, *delivery_type=delivery_data)

    To generate a base delivery, call this:
    >>> delivery(instance, answers, eventBaseDelivery=base_delivery(instance))
    """
    assert len(args) == 1, "Exactly one delivery param required"

    try:
        return ns_application.delivery(
            deliveryHeader=ech_0058_5_0.headerType(
                senderId="https://ebau.apps.be.ch",
                messageId=message_id or str(id(instance)),
                messageType=list(args.keys())[0],
                sendingApplication=pyxb.BIND(
                    manufacturer=camac_metadata.__author__,
                    product=camac_metadata.__title__,
                    productVersion=camac_metadata.__version__,
                ),
                subject=answers["ech-subject"],
                messageDate=message_date or timezone.now(),
                action="1",
                testDeliveryFlag=settings.ENV != "production",
                extension=url or settings.INTERNAL_BASE_URL,
            ),
            **args,
        )
    except (
        IncompleteElementContentError,
        UnprocessedElementContentError,
    ) as e:  # pragma: no cover
        logger.error(e.details())
        raise


def decision_authority(service):
    return ns_application.decisionAuthorityInformationType(
        decisionAuthority=ns_objektwesen.buildingAuthorityType(
            buildingAuthorityIdentificationType=authority(service),
            # description minOccurs=0
            # shortDescription minOccurs=0
            # contactPerson minOccurs=0
            # contact minOccurs=0
            address=ns_address.addressInformationType(
                town=service.get_trans_attr("city") or "unknown",
                swissZipCode=service.zip,
                street=service.address,
                country="CH",
            ),
        )
    )


def requestor(instance: Instance):
    return ns_objektwesen.personType(
        identification=pyxb.BIND(
            personIdentification=ech_0044_4_1.personIdentificationLightType(
                officialName=instance.user.surname
                if instance.user.surname
                else "unknown",
                firstName=instance.user.name if instance.user.name else "unknown",
            )
        )
    )
