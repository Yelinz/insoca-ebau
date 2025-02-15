import Component from "@ember/component";
import { set } from "@ember/object";
import { scheduleOnce } from "@ember/runloop";
import CamacMultipleQuestionRowMixin from "citizen-portal/mixins/camac-multiple-question-row";
import { task } from "ember-concurrency";
import UIkit from "uikit";

import config from "../../config/environment";

export default Component.extend(CamacMultipleQuestionRowMixin, {
  modal: null,

  defaultRequiredValues: null,

  init(...args) {
    this._super(...args);

    this.set(
      "container",
      document.querySelector(config.APP.rootElement || "body")
    );

    this.defaultRequiredValues = {};
    this.columns.forEach(
      (column) => (this.defaultRequiredValues[column.name] = column.required)
    );
  },

  _show() {
    if (!this.isDestroyed) {
      this.set("visible", true);
    }
  },

  _hide() {
    this._value.rollback();

    if (!this.isDestroyed) {
      this.set("visible", false);
    }
  },

  didInsertElement() {
    const id = `#modal-${this.elementId}`;

    this.set("modal", UIkit.modal(id, { container: false }));

    UIkit.util.on(id, "show", () => this._show());
    UIkit.util.on(id, "hide", () => this._hide());
  },

  didReceiveAttrs() {
    scheduleOnce("afterRender", this, this.toggleVisibility);
    if (this.visible) {
      this.send("checkRequired", "firma", this.get("_value.firma"));
    }
  },

  willDestroyElement() {
    this._resetRequiredValues();
    this.modal.hide();
  },

  toggleVisibility() {
    if (this.visible) {
      this.modal.show();
    } else {
      this.modal.hide();
    }
  },

  _resetRequiredValues() {
    this.columns.forEach((column) => {
      set(column, "required", this.defaultRequiredValues[column.name]);
    });
  },

  saveModal: task(function* () {
    this._resetRequiredValues();
    yield this.save.perform();
  }),

  /*
   * Check if firma is set, to set name and vorname as required or not.
   * Should only change required fields in "Personalien" tables since others don't have the field "Firma".
   */
  actions: {
    checkRequired(name, value) {
      if (name === "firma") {
        this.columns.forEach((column) => {
          if (column.name === "name" || column.name === "vorname") {
            set(column, "required", !value);
          }
        });
      }
    },
  },
});
