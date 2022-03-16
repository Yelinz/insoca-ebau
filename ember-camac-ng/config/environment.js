"use strict";

module.exports = function (environment) {
  const ENV = {
    modulePrefix: "camac-ng",
    environment,
    appEnv: process.env.APP_ENV || "development",
    rootURL: "/",
    locationType: "hash",
    podModulePrefix: "camac-ng/ui",
    historySupportMiddleware: true,
    maxDossierImportSize: 1000000000, // 1GB
    apollo: {
      apiURL: "/graphql/",
    },
    EmberENV: {
      FEATURES: {
        // Here you can enable experimental features on an ember canary build
        // e.g. EMBER_NATIVE_DECORATOR_SUPPORT: true
      },
      EXTEND_PROTOTYPES: {
        // Prevent Ember Data from overriding Date.parse.
        Date: false,
      },
    },
    "ember-ebau-core": {
      gisUrl: "/lisag/ows",
      attachmentSections: { applicant: "12000000" },
    },
    APP: {
      rootElement: "#ember-camac-ng",
    },

    APPLICATIONS: {
      kt_bern: {
        prodUrl: "ebau.apps.be.ch",
        gwr: {
          cantonAbbreviation: "BE",
          importModels: ["project"],
        },
        allowApplicantManualWorkItem: false,
        journalDefaultVisibility: false,
        journalEntryDuration: false,
        instanceStates: {
          archived: 20009,
        },
        interchangeableForms: [
          ["baugesuch", "baugesuch-generell", "baugesuch-mit-uvp"],
          ["baugesuch-v2", "baugesuch-generell-v2", "baugesuch-mit-uvp-v2"],
        ],
      },
      kt_schwyz: {
        prodUrl: "behoerden.ebau-sz.ch",
        gwr: {
          cantonAbbreviation: "SZ",
          importModels: ["project", "building", "dwelling"],
        },
        casesQueryOrder: [{ meta: "dossier-number" }],
        allowApplicantManualWorkItem: true,
        journalDefaultVisibility: false,
        journalEntryDuration: true,
        newCase: {
          calumaWorkflow: "internal-document",
          camacForm: 11,
        },
        caseTableColumns: {
          caluma: ["dossierNr", "caseDocumentFormName", "intent", "caseStatus"],
          "camac-ng": [
            "dossierNr",
            "instanceFormDescription",
            "locationSZ",
            "builderSZ",
            "intentSZ",
            "instanceStateDescription",
          ],
        },
        activeCaseFilters: {
          caluma: [
            "dossierNumber",
            "intent",
            "caseStatus",
            "caseDocumentFormName",
          ],
          "camac-ng": [
            "instanceIdentifier",
            "instanceStateDescription",
            "locationSZ",
            "responsibleServiceUser",
            "addressSZ",
            "plotSZ",
            "builderSZ",
            "landownerSZ",
            "applicantSZ",
            "submitDateAfterSZ",
            "submitDateBeforeSZ",
            "serviceSZ",
            "formSZ",
          ],
        },
        intentSlugs: ["voranfrage-vorhaben"],
        externalServiceGroupIds: [],
        caseTableFormFields: [
          "bauherrschaft",
          "bauherrschaft-v2",
          "bauherrschaft-override",
          "bezeichnung",
          "bezeichnung-override",
        ],
      },
      kt_uri: {
        prodUrl: "urec.ur.ch",
        gwr: {
          cantonAbbreviation: "UR",
          importModels: ["project", "building", "dwelling"],
        },
        casesQueryOrder: [
          { documentAnswer: "municipality" },
          { meta: "dossier-number", direction: "DESC" },
        ],
        allowApplicantManualWorkItem: false,
        journalDefaultVisibility: true,
        journalEntryDuration: false,
        activeCirculationStates: [
          1, // RUN
          41, // NFD
        ],
        allowedInstanceLinkingGroups: [
          142, // KOOR BG
          21, // KOOR NP
        ],
        caseTableColumns: {
          caluma: {
            municipality: [
              "instanceId",
              "dossierNr",
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
              "dossierNr",
              "circulationInitializerService",
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
              "dossierNr",
              "circulationInitializerService",
              "form",
              "municipality",
              "applicant",
              "intent",
              "street",
              "processingDeadline",
            ],
            default: [
              "dossierNr",
              "municipality",
              "applicant",
              "intent",
              "street",
              "parcelNumbers",
            ],
          },
        },
        activeCaseFilters: {
          caluma: [
            "instanceId",
            "dossierNumber",
            "applicantName",
            "street",
            "municipality",
            "parcelNumber",
            "instanceState",
            "service",
            "pendingSanctionsControlInstance",
            "buildingPermitType",
            "createdAfter",
            "createdBefore",
            "intent",
          ],
        },
        intentSlugs: [
          "proposal-description",
          "beschreibung-zu-mbv",
          "bezeichnung",
          "vorhaben-proposal-description",
          "veranstaltung-beschrieb",
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
      },
    },

    // this will be overwritten by one of the canton specific configurations
    // above
    APPLICATION: {},
  };

  if (environment === "development") {
    ENV["ember-ebau-core"].gisUrl = "http://camac-ng.local/lisag/ows";
  }

  if (environment === "test") {
    // Testem prefers this...
    ENV.locationType = "none";

    // keep test console output quieter
    ENV.APP.LOG_ACTIVE_GENERATION = false;
    ENV.APP.LOG_VIEW_LOOKUPS = false;

    ENV.APP.rootElement = "#ember-testing";
    ENV.APP.autoboot = false;
  }

  if (environment === "production") {
    // here you can enable a production-specific feature
  }

  ENV.APPLICATION = ENV.APPLICATIONS[process.env.APPLICATION || "kt_bern"];
  ENV.routerScroll = { targetElement: ENV.APP.rootElement };

  return ENV;
};
