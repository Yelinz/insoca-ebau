import { setupTest } from "ember-qunit";
import { module, test } from "qunit";

module("Unit | Route | instances/edit/grundinformationen/index", function(
  hooks
) {
  setupTest(hooks);

  test("it exists", function(assert) {
    const route = this.owner.lookup(
      "route:instances/edit/grundinformationen/index"
    );
    assert.ok(route);
  });
});
