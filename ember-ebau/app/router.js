import EmberRouter from "@ember/routing/router";
import config from "ebau/config/environment";

export default class Router extends EmberRouter {
  location = config.locationType;
  rootURL = config.rootURL;
}

const resetNamespace = true;

Router.map(function () {
  this.route("login");
  this.route("protected", { path: "/" }, function () {
    this.route("dashboard", { path: "/dashboard/:type", resetNamespace });
    this.route("cases", { resetNamespace }, function () {
      this.route("detail", { path: "/:case_id" }, function () {
        this.route("form");
        this.route("work-items", function () {
          this.route("edit", { path: "/:work_item_id" });
          this.route("new");
        });
        this.route("journal");
        this.route("history");
      });
      this.route("new");
    });
  });
});
