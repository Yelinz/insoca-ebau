import { setupTest } from "ember-qunit";
import { module, test } from "qunit";

module("Unit | Route | instances/edit/fachthemen/reklamen", function(hooks) {
  setupTest(hooks);

  test("it exists", function(assert) {
    const route = this.owner.lookup("route:instances/edit/fachthemen/reklamen");
    assert.ok(route);
  });
});
