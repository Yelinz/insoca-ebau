import { getOwner } from "@ember/application";
import { A } from "@ember/array";
import Component from "@ember/component";
import { computed } from "@ember/object";
import { inject as service } from "@ember/service";
import { queryManager } from "ember-apollo-client";
import saveDocumentMutation from "ember-caluma/gql/mutations/save-document";
import Document from "ember-caluma/lib/document";
import { parseDocument } from "ember-caluma/lib/parsers";
import { task } from "ember-concurrency";
import { all } from "rsvp";

const KEY_TABLE_FORM = "parzelle-tabelle";
const KEY_TABLE_QUESTION = "parzelle";
const KEY_TABLE_PARCEL = "parzellennummer";
const KEY_TABLE_BAURECHT = "baurecht-nummer";
const KEY_TABLE_EGRID = "e-grid-nr";
const KEY_TABLE_COORD_NORTH = "lagekoordinaten-nord";
const KEY_TABLE_COORD_EAST = "lagekoordinaten-ost";
const KEYS_TABLE = [
  KEY_TABLE_PARCEL,
  KEY_TABLE_BAURECHT,
  KEY_TABLE_EGRID,
  KEY_TABLE_COORD_NORTH,
  KEY_TABLE_COORD_EAST
];

const KEY_SIMPLE_MAP = "karte-einfache-vorabklaerung";
const KEY_SIMPLE_PARCEL = "parzellennummer";
// The question baurecht-nummer is not present in the simple form.
//const KEY_SIMPLE_BAURECHT = "baurecht-nummer";
const KEY_SIMPLE_EGRID = "e-grid-nr";
const KEY_SIMPLE_COORD_NORTH = "lagekoordinaten-nord-einfache-vorabklaerung";
const KEY_SIMPLE_COORD_EAST = "lagekoordinaten-ost-einfache-vorabklaerung";
const KEYS_SIMPLE = [
  KEY_SIMPLE_MAP,
  KEY_SIMPLE_PARCEL,
  //KEY_SIMPLE_BAURECHT,
  KEY_SIMPLE_EGRID,
  KEY_SIMPLE_COORD_NORTH,
  KEY_SIMPLE_COORD_EAST
];
const KEYS_SIMPLE_HASH = {
  [KEY_SIMPLE_COORD_NORTH]: KEY_TABLE_COORD_NORTH,
  [KEY_SIMPLE_COORD_EAST]: KEY_TABLE_COORD_EAST
};

const REGEXP_ORIGIN = /^(https?:\/\/[^/]+)/i;

const FIELD_MAP = {
  ARCHINV_FUNDST: {
    path: "gebiet-mit-archaeologischen-objekten",
    values: {
      true: "gebiet-mit-archaeologischen-objekten-ja",
      false: "gebiet-mit-archaeologischen-objekten-nein"
    }
  },
  BALISKBS_KBS: {
    path: "belasteter-standort",
    values: {
      true: "belasteter-standort-ja",
      false: "belasteter-standort-nein"
    }
  },
  BAUINV_BAUINV_VW: {
    path: "handelt-es-sich-um-ein-baudenkmal",
    values: {
      true: "handelt-es-sich-um-ein-baudenkmal-ja",
      false: "handelt-es-sich-um-ein-baudenkmal-nein"
    }
  },
  GK5_SY: {
    path: "gebiet-mit-naturgefahren",
    values: {
      true: "gebiet-mit-naturgefahren-ja",
      false: "gebiet-mit-naturgefahren-nein"
    }
  },
  // The question GSK25_GSK_VW is not present in our form.
  //GSK25_GSK_VW: {},
  GSKT_BEZEICH_DE: {
    path: "gewaesserschutzbereich",
    values: {
      "übriger Bereich üB": "gewaesserschutzbereich-ueb",
      "Gewässerschutzbereich Ao": "gewaesserschutzbereich-ao",
      "Gewässerschutzbereich Au": "gewaesserschutzbereich-au",
      "Provisorischer Zuströmbereich Zu": "gewaesserschutzbereich-zu"
    }
  },
  NSG_NSGP: {
    path: "naturschutz",
    values: {
      true: "naturschutz-ja",
      false: "naturschutz-nein"
    }
  },
  UZP_BAU_VW: {
    path: "nutzungszone"
  },
  UZP_LSG_VW: {
    path: "objekt-des-besonderen-landschaftsschutzes",
    values: {
      true: "objekt-des-besonderen-landschaftsschutzes-ja",
      false: "objekt-des-besonderen-landschaftsschutzes-nein"
    }
  },
  UZP_UEO_VW: {
    path: "ueberbauungsordnung"
  }
};

/**
 * Combine the values of all parcels to one array by
 * - Boolean: True if at least one parcel is true
 * - String, Array: Concat all unique values
 *
 * There's a test in php/kt_bern/public/js-dev/test/reduce-test.js
 */
function reduceArrayValues(data) {
  return data.reduce((result, curr) => {
    [...new Set([...Object.keys(result), ...Object.keys(curr)])].forEach(
      key => {
        if (!curr[key]) {
          curr[key] = result[key];
        } else if (!result[key]) {
          result[key] = curr[key];
        } else if (typeof curr[key] === "string" && result[key]) {
          result[key] = result[key].includes(curr[key])
            ? result[key]
            : `${result[key]}, ${curr[key]}`;
        } else if (Array.isArray(curr[key])) {
          result[key] = [...new Set([...result[key], ...curr[key]])];
        } else {
          result[key] = Boolean(result[key] || curr[key]);
        }
      }
    );
    return result;
  });
}

// ?
// use Cross Domain Communication
// Activate view linking
// View
// Basemap
// Send active tool callback
// Key name for the search
// Value we are searching for
// Returning E-Grid number, Parcel number (GSTBEZ) and project status (PROJSTAT)
// Base Info
// Map Content
// Tools
// Tools- Add/Remove

export default Component.extend({
  notification: service(),
  fetch: service(),
  intl: service(),
  calumaStore: service(),

  apollo: queryManager(),

  classNames: ["gis-map"],

  disabled: false,
  parcels: null,
  gisData: null,
  showInstructions: false,
  showConfirmation: false,

  confirmField: computed("field", function() {
    return this.field.document.findField("bestaetigung-gis");
  }),

  confirmFieldUnchecked: computed("confirmField.value.[]", function() {
    return (
      !this.get("confirmField.hidden") &&
      this.get("confirmField.value.length") !== 1
    );
  }),

  link: computed(function() {
    // This try/catch block is necessary as long as we don't have a mock
    // backend for the integration tests.
    try {
      // GET FIRST E-GRID NUMBER FOR CURRENT PARCELS
      // Find the table with the parcels.
      const table = this.field.document.fields.find(
        field => field.question.slug === KEY_TABLE_QUESTION
      );
      // Find the E-Grid field of the first parcel.
      const rows = table && table.answer.value;
      const field =
        rows &&
        rows[0].fields.find(field => field.question.slug === KEY_TABLE_EGRID);
      // Set the selection and egrid variables.
      const selection = field && field.answer.value;
      const egrid = selection ? selection : "EGRID";

      const search = [
        "baseURL=https://www.map.apps.be.ch/pub",
        "project=a42pub_ebau_cl",
        "map_adv=true",
        "useXD=true",
        "linked_view=true",
        "view=Grundstuecke / Parcelles 1:6000",
        "basemapview=HK_Hintergrund_bunt",
        "callback_active_tool=activeToolResult",
        "query=Suche_EBAU_DIPANU",
        "keyname=EGRID",
        `keyvalue=${egrid}`,
        "returnkey=EGRID;GSTBEZ;PROJSTAT",
        "callback_addremove_mw=addremoveResult",
        "retainSelection=true",
        ...(this.disabled
          ? ["activetools=NAVIGATION VIEW"]
          : [
              "activetools=NAVIGATION VIEW ADDREMOVE FTS",
              "callback_fts_mw=ftsResult",
              "fts_search=true",
              ...(selection ? [] : ["startmode=FTS"])
            ])
      ].join("&");

      return `https://www.map.apps.be.ch/pub/client_mapwidget/default.jsp?${search}`;
    } catch (error) {
      /* eslint-disable-next-line no-console */
      console.log(error);
      return null;
    }
  }),

  origin: computed("link", function() {
    // The regular expression extracts the scheme and hostname from the link.
    // We need this to check if the "message" events were sent by the iframe.
    return REGEXP_ORIGIN.test(this.link) && this.link.match(REGEXP_ORIGIN)[1];
  }),

  /**
   * The message event handler which invokes
   * the right method with the relevant arguments.
   *
   * `event.data` array structure:
   * 0: GIS functionality
   * 1: callback name
   * 2: features
   * 3: coordinate x (computed)
   * 4: coordinate y (computed)
   * 5: query success result (true|false)
   * 6: EGRIDs
   * 7: map scales
   * 8: map coordSys (informations concerning the map
   *
   * @method receiveMessage
   * @param {Event} event The DOM "message" event.
   */
  receiveMessage(event) {
    if (event.origin !== this.origin) {
      return;
    }

    const [action, , features] = event.data;

    return this.parseResult(action, features);
  },

  /**
   * Filter and parses the event response
   * and update the `parcels` property.
   *
   * @method addremoveResult
   * @param {Object} features The features sent by the iframe/map.
   */
  parseResult(action, features) {
    if (!["ADDREMOVE", "FTS"].includes(action)) {
      return;
    }
    const isSearchResult = action === "FTS";
    const prop = isSearchResult ? "FEATURES" : "COORDS";
    // Return if there aren't values
    if (
      features === null ||
      features[prop] === null ||
      features[prop].length === 0
    ) {
      return;
    }

    // Return if search result doesn't contain parcel information
    if (!features.keyname.includes("EGRID")) {
      return;
    }

    // Setting up features indexes
    let parcel_feature_index = 0;
    let egrid_feature_index = 0;
    let project_status_index = 0;

    features.keyname.forEach((keyname, index) => {
      switch (keyname) {
        case "GSTBEZ":
          parcel_feature_index = index;
          break;
        case "EGRID":
          egrid_feature_index = index;
          break;
        case "PROJSTAT":
          project_status_index = index;
          break;
      }
    });

    // Temporary object to store results, will be converted to an array at the end
    const parcels = {};

    features[prop].forEach(coords => {
      const projectStatus = coords.keyvalue[project_status_index];

      // Keep the value only if the status is "valid"
      if (["0", "gültig", "valable"].includes(projectStatus)) {
        let parcel_number = "";
        let baurecht_number = "";

        // If the value contains the "BR" string, then it is the "Baurecht" number
        if (coords.keyvalue[parcel_feature_index].includes("BR")) {
          baurecht_number = coords.keyvalue[parcel_feature_index];
        } else {
          parcel_number = coords.keyvalue[parcel_feature_index];
        }

        const xProp = isSearchResult ? "coord_x" : "xgeo";
        const yProp = isSearchResult ? "coord_y" : "ygeo";

        // Create the parcel object
        const parcel = {
          [KEY_TABLE_PARCEL]: parcel_number,
          [KEY_TABLE_BAURECHT]: baurecht_number,
          [KEY_TABLE_EGRID]: coords.keyvalue[egrid_feature_index],
          [KEY_TABLE_COORD_EAST]: parseInt(coords[xProp]),
          [KEY_TABLE_COORD_NORTH]: parseInt(coords[yProp])
        };

        const parcel_key = `${coords[xProp]}.${coords[yProp]}`;

        if (parcel_key in parcels) {
          const oldParcel = parcels[parcel_key];

          if (parcel_number !== "") {
            // We are currently handling the "Baurecht" parcel, so take only that value
            parcel[KEY_TABLE_BAURECHT] = oldParcel[KEY_TABLE_BAURECHT];
          } else {
            // Take all the other values and overwrite the "Baurecht" ones
            parcel[KEY_TABLE_PARCEL] = oldParcel[KEY_TABLE_PARCEL];
            parcel[KEY_TABLE_EGRID] = oldParcel[KEY_TABLE_EGRID];
            parcel[KEY_TABLE_COORD_EAST] = oldParcel[KEY_TABLE_COORD_EAST];
            parcel[KEY_TABLE_COORD_NORTH] = oldParcel[KEY_TABLE_COORD_NORTH];
          }
        }

        parcels[parcel_key] = parcel;
      }
    });

    this.set("parcels", Object.values(parcels));
  },

  /**
   * Saves the parcel values in their corresponding fields from the
   * current document. This method is used for the preliminary assessment
   * and only allows for one parcel.
   *
   * @method populateFields
   * @param {Array} parcels The parcels prepared by `addremoveResult`.
   */
  populateFields: task(function*(parcels) {
    const [parcel] = parcels;
    const fields = this.field.document.fields.filter(field =>
      KEYS_SIMPLE.includes(field.question.slug)
    );

    yield all(
      fields.map(async field => {
        const slug =
          KEYS_SIMPLE_HASH[field.question.slug] || field.question.slug;
        const value = String(parcel[slug]);

        if (value !== null && value.length > 0) {
          field.answer.set("value", value);

          await field.save.perform();
          await field.validate.perform();
        }
      })
    );
  }),

  /**
   * Creates a new document for each parcel and saves the parcel values
   * in their corresponding fields. This method is used for all workflows
   * except the preliminary assessment.
   *
   * @method populateTable
   * @param {Array} parcels The parcels prepared by `addremoveResult`.
   */
  populateTable: task(function*(parcels) {
    // Locate the target table for the parcel data.
    const table = this.field.document.fields.find(
      field => field.question.slug === KEY_TABLE_QUESTION
    );

    // Prepare the mutation to create a new row.
    const mutation = {
      mutation: saveDocumentMutation,
      variables: { input: { form: KEY_TABLE_FORM } }
    };

    // Start with an empty set of rows as we currently overwrite previous rows.
    const rows = [];

    // Create, populate, and add a new row for each parcel.
    yield all(
      parcels.map(async parcel => {
        const newDocumentRaw = await this.apollo.mutate(
          mutation,
          "saveDocument.document"
        );

        const newDocument = this.calumaStore.push(
          Document.create(getOwner(this).ownerInjection(), {
            raw: parseDocument(newDocumentRaw)
          })
        );

        const fields = newDocument.fields.filter(field =>
          KEYS_TABLE.includes(field.question.slug)
        );

        await all(
          fields.map(async field => {
            const { slug } = field.question;
            const value = String(parcel[slug]);

            if (value !== null && value.length > 0) {
              field.answer.set("value", value);

              await field.save.perform();
              await field.validate.perform();
            }
          })
        );

        rows.push(newDocument);
      })
    );

    table.answer.set("value", rows);

    yield table.save.perform();
    yield table.validate.perform();
  }),

  fetchAdditionalData: task(function*(parcels) {
    this.set("gisData", A());

    const responses = yield all(
      parcels.map(
        async parcel =>
          await this.fetch.fetch(`/api/v1/egrid/${parcel[KEY_TABLE_EGRID]}`)
      )
    );

    const success = responses.every(response => response.ok);

    if (success) {
      const raw = yield all(
        responses.map(res => res.json().then(({ data }) => data))
      );

      Object.entries(FIELD_MAP).forEach(([key, { path, values }]) => {
        const field = this.field.document.findField(path);
        const type = field.question.__typename;
        let value = reduceArrayValues(raw)[key];
        let valuePretty = value;

        if (value === undefined) {
          return;
        }

        if (type === "ChoiceQuestion") {
          value = values[value];
          valuePretty = field.question.choiceOptions.edges.find(
            edge => edge.node.slug === value
          ).node.label;
        } else if (type === "MultipleChoiceQuestion") {
          value = Array.isArray(value) ? value : [value];
          value = value.map(val => values[val]);
          valuePretty = field.question.multipleChoiceOptions.edges
            .filter(edge => edge.node.slug.includes(value))
            .map(edge => edge.node.label);
        } else if (Array.isArray(value)) {
          value = value.join(", ");
          valuePretty = value;
        }

        this.gisData.pushObject({ field, value, valuePretty });
      });

      this.set("showConfirmation", true);
    } else {
      this.notification.danger(
        this.intl.t("gis.notifications.error-additional")
      );
    }
  }),

  init(...args) {
    this._super(...args);
    this.receiveMessage = this.receiveMessage.bind(this);
  },

  didInsertElement(...args) {
    this._super(...args);
    window.addEventListener("message", this.receiveMessage);
  },

  willDestroyElement(...args) {
    window.removeEventListener("message", this.receiveMessage);
    this._super(...args);
  },

  saveAdditionalData: task(function*() {
    yield all(
      this.gisData.map(async ({ field, value }) => {
        field.answer.set("value", value);

        await field.save.perform();
        await field.validate.perform();
      })
    );

    this.set("showConfirmation", false);
  }),

  actions: {
    applySelection() {
      if (this.parcels && this.parcels.length) {
        if (this.field.question.slug === KEY_SIMPLE_MAP) {
          if (this.parcels.length > 1) {
            this.notification.danger(this.intl.t("gis.notifications.max-one"));
          } else {
            this.populateFields.perform(this.parcels);
          }
        } else {
          if (this.parcels.length > 20) {
            this.notification.danger(
              this.intl.t("gis.notifications.max-twenty")
            );
          } else {
            this.populateTable.perform(this.parcels);
            this.fetchAdditionalData.perform(this.parcels);
          }
        }
      } else {
        this.notification.danger(this.intl.t("gis.notifications.min-one"));
      }
    }
  }
});
