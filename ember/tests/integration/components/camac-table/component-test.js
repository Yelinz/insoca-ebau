import { render, click, fillIn } from "@ember/test-helpers";
import loadQuestions from "citizen-portal/tests/helpers/load-questions";
import { setupMirage } from "ember-cli-mirage/test-support";
import { setupRenderingTest } from "ember-qunit";
import hbs from "htmlbars-inline-precompile";
import { module, test } from "qunit";

module("Integration | Component | camac-table", function(hooks) {
  setupRenderingTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(async function() {
    const instance = this.server.create("instance");

    this.set("instance", instance);

    this.server.create("form-field", {
      name: "test",
      instance,
      value: [
        {
          f1: "test",
          f2: "test",
          f3: "1",
          f4: ["1", "2"],
          f5: "1",
          f6: ["1", "2"]
        }
      ]
    });

    this.server.get("/api/v1/form-config", () => ({
      questions: {
        test: {
          label: "only for testing",
          required: true,
          type: "table",
          config: {
            columns: [
              { name: "f1", label: "field 1", type: "text", config: {} },
              { name: "f2", label: "field 2", type: "number", config: {} },
              {
                name: "f3",
                label: "field 3",
                type: "radio",
                config: { options: ["1", "2", "3"] }
              },
              {
                name: "f4",
                label: "field 4",
                type: "checkbox",
                config: { options: ["1", "2", "3"] }
              }
            ]
          }
        }
      }
    }));

    await loadQuestions(["test"], instance.id);
  });

  test("it renders", async function(assert) {
    assert.expect(2);

    await render(hbs`{{camac-table 'test' instance=instance}}`);

    assert.dom("table").exists();
    assert.dom("tbody > tr > td:first-child").hasText("test");
  });

  test("it can delete a row", async function(assert) {
    assert.expect(2);

    await render(hbs`{{camac-table 'test' instance=instance}}`);

    assert.dom("tbody > tr > td:first-child").hasText("test");

    await click("button[data-test-delete-row]");

    assert
      .dom("tbody > tr > td:first-child")
      .hasText("Noch keine Einträge erfasst");
  });

  test("it can edit a row", async function(assert) {
    assert.expect(2);

    await render(hbs`{{camac-table 'test' instance=instance}}`);

    assert.dom("tbody > tr > td:first-child").hasText("test");

    await click("button[data-test-edit-row]");
    await fillIn("input[type=text]", "shimmyshimmyya");
    await fillIn("input[type=number]", "123");
    await click(".uk-button-primary");

    assert.dom("tbody > tr > td:first-child").hasText("shimmyshimmyya");
  });

  test("it can add a row", async function(assert) {
    assert.expect(2);

    await render(hbs`{{camac-table 'test' instance=instance}}`);

    assert.dom("tbody > tr").exists({ count: 1 });

    await click("tfoot > tr > td:first-child > button");
    await click(".uk-button-primary");

    assert.dom("tbody > tr").exists({ count: 2 });
  });
});
