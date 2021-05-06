"use strict";

module.exports = function (environment) {
  const ENV = {
    modulePrefix: "camac-ng",
    environment,
    rootURL: "/",
    locationType: "hash",
    podModulePrefix: "camac-ng/ui",
    historySupportMiddleware: true,
    apollo: {
      apiURL: "/graphql/",
    },
    moment: {
      includeLocales: require("./locales"),
      allowEmpty: true,
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
      gisUrl: "https://service.lisag.ch/ows",
      attachmentSections: { applicant: "12000000" },
    },
    APP: {
      rootElement: "#ember-camac-ng",
    },

    APPLICATIONS: {
      kt_bern: {
        allowApplicantManualWorkItem: false,
        instanceStates: {
          archived: 20009,
        },
        interchangeableForms: [
          "baugesuch",
          "baugesuch-generell",
          "baugesuch-mit-uvp",
        ],
      },
      kt_schwyz: {
        allowApplicantManualWorkItem: true,
      },
      kt_uri: {
        allowApplicantManualWorkItem: false,
        activeCirculationStates: [
          1, // RUN
          41, // NFD
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
