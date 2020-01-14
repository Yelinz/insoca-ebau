"use strict";

module.exports = function(environment) {
  const oidcHost =
    process.env.KEYCLOAK_URL || "http://camac-ng-keycloak.local/auth";

  const ENV = {
    modulePrefix: "ember-caluma-portal",
    environment,
    rootURL: "/",
    locationType: "auto",
    historySupportMiddleware: true,
    oidcHost,
    "ember-simple-auth-oidc": {
      host: `${oidcHost.replace(
        /\/$/,
        ""
      )}/realms/ebau/protocol/openid-connect`,
      clientId: "portal",
      authEndpoint: "/auth",
      tokenEndpoint: "/token",
      endSessionEndpoint: "/logout",
      userinfoEndpoint: "/userinfo",
      afterLogoutUri: "/",
      forwardParams: ["kc_idp_hint"]
    },
    apollo: {
      apiURL: "/graphql/"
    },
    EmberENV: {
      FEATURES: {
        // Here you can enable experimental features on an ember canary build
        // e.g. EMBER_NATIVE_DECORATOR_SUPPORT: true
      },
      EXTEND_PROTOTYPES: {
        // Prevent Ember Data from overriding Date.parse.
        Date: false
      }
    },

    APP: {
      // Here you can pass flags/options to your application instance
      // when it is created
    },
    moment: {
      includeLocales: ["de", "fr"]
    },

    languages: ["de", "fr"],
    fallbackLanguage: "de",

    ebau: {
      claims: {
        notificationTemplateId: 32,
        attachmentSectionId: 7
      },
      attachments: {
        allowedMimetypes: ["image/png", "image/jpeg", "application/pdf"]
      }
    }
  };

  if (environment === "development") {
    // ENV.APP.LOG_RESOLVER = true;
    // ENV.APP.LOG_ACTIVE_GENERATION = true;
    // ENV.APP.LOG_TRANSITIONS = true;
    // ENV.APP.LOG_TRANSITIONS_INTERNAL = true;
    // ENV.APP.LOG_VIEW_LOOKUPS = true;
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

  return ENV;
};
