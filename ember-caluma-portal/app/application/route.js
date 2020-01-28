import { getOwner } from "@ember/application";
import { get } from "@ember/object";
import Route from "@ember/routing/route";
import { inject as service } from "@ember/service";
import OIDCApplicationRouteMixin from "ember-simple-auth-oidc/mixins/oidc-application-route-mixin";

const RouteClass = Route.extend(OIDCApplicationRouteMixin);

export default class ApplicationRouter extends RouteClass {
  @service session;
  @service router;
  @service calumaOptions;

  beforeModel(transition) {
    const { language, group } = get(transition, "to.queryParams") || {};

    this.session.set("language", language || this.session.language);
    this.session.set("data.group", group || this.session.group);

    if (window.top !== window) {
      getOwner(this)
        .lookup("service:-document")
        .querySelector("body")
        .classList.add("embedded");
    }

    this.calumaOptions.registerComponentOverride({
      label: "Karte",
      component: "be-gis"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Einreichen Button",
      component: "be-submit-instance",
      type: "CheckboxQuestion"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Dokument Formular",
      component: "be-documents-form",
      type: "FormQuestion"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Download (PDF)",
      component: "be-download-pdf",
      type: "StaticQuestion"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Nachforderungen Tabelle",
      component: "be-claims-table",
      type: "TableQuestion"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Nachforderungen Formular",
      component: "be-claims-form",
      type: "Form"
    });
    this.calumaOptions.registerComponentOverride({
      label: "Versteckt",
      component: "be-hidden-input"
    });
  }
}
