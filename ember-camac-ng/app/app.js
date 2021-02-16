import Application from "@ember/application";
import loadInitializers from "ember-load-initializers";
import Resolver from "ember-resolver";

import config from "camac-ng/config/environment";

// Intl polyfills
import "@formatjs/intl-locale/polyfill";
import "@formatjs/intl-getcanonicallocales/polyfill";
import "@formatjs/intl-pluralrules/polyfill";
import "@formatjs/intl-pluralrules/locale-data/de";
import "@formatjs/intl-pluralrules/locale-data/fr";
import "@formatjs/intl-relativetimeformat/polyfill";
import "@formatjs/intl-relativetimeformat/locale-data/de";
import "@formatjs/intl-relativetimeformat/locale-data/fr";

// Array polyfills (flat, flatMap)
import "core-js/es/array";

export default class App extends Application {
  modulePrefix = config.modulePrefix;
  podModulePrefix = config.podModulePrefix;
  rootElement = config.APP.rootElement;

  Resolver = Resolver;

  engines = {
    emberCaluma: {
      dependencies: {
        services: [
          "apollo", // ember-apollo-client for graphql
          "notification", // ember-uikit for notifications
          "router", // ember router for navigation
          "intl", // ember-intl for i18n
          "caluma-options", // service to configure ember-caluma
          "validator", // service for generic regex validation
        ],
      },
    },
    emberEbauGwr: {
      dependencies: {
        services: [
          "notification", // ember-uikit for notifications
          "intl", // ember-intl for i18n
          { config: "gwr-config" }, // service to configure ember-ebau-gwr
        ],
      },
    },
  };
}

loadInitializers(App, config.modulePrefix);
