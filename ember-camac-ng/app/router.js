import EmberRouterScroll from "ember-router-scroll";

import config from "camac-ng/config/environment";

export default class Router extends EmberRouterScroll {
  location = config.locationType;
  rootURL = config.rootURL;
}

/* eslint-disable-next-line array-callback-return */
Router.map(function () {
  this.route("organisation");
  this.route("history", { path: "/instances/:instance_id/history" });
  this.route("journal", { path: "/instances/:instance_id/journal" });
  this.route("work-items", function () {
    this.route(
      "instance",
      {
        path: "instances/:instance_id/work-items",
      },
      function () {
        this.route("edit", { path: "/:work_item_id" });
        this.route("new");
      }
    );
  });
  this.route("form", { path: "/instances/:id/form" });

  this.mount("ember-caluma", {
    as: "form-builder",
    path: "/form-builder",
    resetNamespace: true,
  });
  this.mount("ember-ebau-gwr", { as: "gwr", path: "/gwr/:id" });
  this.route("cases", function () {
    this.route("detail", { path: "/:case_id" }, function () {
      this.route("dashboard");
    });
  });
  this.route("audit", { path: "instances/:instance_id/audit" }, function () {
    this.route("edit", { path: "/edit/:document_uuid" });
  });
  this.route("support", { path: "instances/:instance_id/support" });
  this.route("responsible", { path: "instances/:instance_id/responsible" });
  this.route(
    "publication",
    { path: "instances/:instance_id/publication" },
    function () {
      this.route("edit", { path: "/edit/:workitem_uuid" });
    }
  );
});
