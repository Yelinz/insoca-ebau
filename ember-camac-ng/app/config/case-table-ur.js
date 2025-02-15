export default {
  columns: {
    caluma: {
      municipality: [
        "instanceId",
        "dossierNumber",
        "form",
        "municipality",
        "user",
        "applicant",
        "intent",
        "street",
        "instanceState",
      ],
      coordination: [
        "instanceId",
        "dossierNumber",
        "circulationInitializerServices",
        "form",
        "municipality",
        "user",
        "applicant",
        "intent",
        "street",
        "instanceState",
      ],
      service: [
        "deadlineColor",
        "instanceId",
        "dossierNumber",
        "circulationInitializerServices",
        "form",
        "municipality",
        "applicant",
        "intent",
        "street",
        "responsibility",
        "processingDeadline",
      ],
      default: [
        "dossierNumber",
        "municipality",
        "applicant",
        "intent",
        "street",
        "parcel",
      ],
    },
  },
  activeFilters: {
    caluma: [
      "instanceId",
      "dossierNumber",
      "applicant",
      "address",
      "municipality",
      "parcel",
      "instanceState",
      "service",
      "pendingSanctionsControlInstance",
      "buildingPermitType",
      "submitDateAfter",
      "submitDateBefore",
      "intent",
      "withCantonalParticipation",
      "responsibleServiceUser",
    ],
  },
  activeCirculationStates: [
    1, // RUN
    41, // NFD
  ],
  externalServiceGroupIds: [
    "21",
    "70",
    "2",
    "65",
    "66",
    "62",
    "61",
    "63",
    "64",
    "41",
    "71",
  ],
  availableOrderings: {
    municipality: {
      caluma: [
        { documentAnswer: "municipality" },
        { meta: "dossier-number", direction: "DESC" },
      ],
    },
    instanceState: {
      "camac-ng": ["instance__instance_state__name"],
    },
    instanceId: {
      caluma: [{ meta: "camac-instance-id" }],
    },
    dossierNumber: {
      caluma: [{ meta: "dossier-number" }],
    },
  },
  defaultOrder: "municipality",
  pageSize: 20,
};
