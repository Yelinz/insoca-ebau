import { render } from "@ember/test-helpers";
import { hbs } from "ember-cli-htmlbars";
import setupMirage from "ember-cli-mirage/test-support/setup-mirage";
import { setupIntl } from "ember-intl/test-support";
import { setupRenderingTest } from "ember-qunit";
import { module, test } from "qunit";

module("Integration | Component | cf-text-textcomponent", function (hooks) {
  setupRenderingTest(hooks);
  setupMirage(hooks);
  setupIntl(hooks);

  test("it renders", async function (assert) {
    this.set("field", { answer: { value: "" } });

    await render(hbs`<CfTextTextcomponent  @field={{@field}}/>`);

    assert.equal(this.element.textContent.trim(), "t:global.empty:()");
  });
});
