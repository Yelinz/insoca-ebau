import { render, click, fillIn } from "@ember/test-helpers";
import loadQuestions from "citizen-portal/tests/helpers/load-questions";
import { setupMirage } from "ember-cli-mirage/test-support";
import { setupRenderingTest } from "ember-qunit";
import hbs from "htmlbars-inline-precompile";
import { module, test } from "qunit";

module("Integration | Component | camac-gwr", function (hooks) {
  setupRenderingTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(async function () {
    const instance = this.server.create("instance");

    this.set("instance", instance);

    this.building = this.server.create("form-field", {
      name: "test-gwr",
      instance,
      value: [
        {
          uuid: "testuuid",
          gebaeudebezeichnung: "test gebäude",
          adresse: "test",
          f2: "2",
          f3: "1",
          f4: ["1", "2"],
          f5: "1",
          f6: ["1", "2"],
          f7: [
            {
              col1: "test",
            },
          ],
        },
      ],
    });

    this.server.get("/api/v1/form-config", () => {
      return {
        questions: {
          "test-gwr": {
            type: "gwr",
            required: true,
            config: {
              columns: [
                {
                  name: "gebaeudebezeichnung",
                  label: "f0",
                  type: "text",
                  required: true,
                  config: {},
                },
                {
                  name: "adresse",
                  label: "f1",
                  type: "text",
                  required: true,
                  config: {},
                },
                {
                  name: "f2",
                  label: "f2",
                  type: "number",
                  required: true,
                  config: {},
                },
                {
                  name: "f3",
                  label: "f3",
                  type: "radio",
                  required: true,
                  config: { options: ["1", "2", "3"] },
                },
                {
                  name: "f4",
                  label: "f4",
                  type: "checkbox",
                  required: false,
                  config: { options: ["1", "2", "3"] },
                },
                {
                  name: "f5",
                  label: "f5",
                  type: "table",
                  required: true,
                  config: {
                    columns: [
                      {
                        name: "col1",
                        label: "col1",
                        type: "text",
                        required: true,
                      },
                    ],
                  },
                },
              ],
            },
          },
        },
      };
    });

    await loadQuestions(["test-gwr"], instance.id);
  });

  test("it renders a GWR", async function (assert) {
    assert.expect(2);

    await render(
      hbs`{{camac-gwr 'test-gwr' instance=instance readonly=false}}`
    );

    assert.dom(".uk-card").exists({ count: 2 });
    assert.dom(".uk-card:first-child").hasText("test gebäude");
  });

  test("it can edit a building", async function (assert) {
    assert.expect(4);

    await render(
      hbs`{{camac-gwr 'test-gwr' instance=instance readonly=false}}`
    );

    assert.dom(".uk-card").exists({ count: 2 });
    assert.dom(".uk-card:first-child").hasText("test gebäude");

    await click(`[data-test-gwr-building=${this.building.value[0].uuid}]`);

    assert.dom(".uk-card").exists({ count: 3 });

    await fillIn(
      ".uk-card:last-child .uk-margin:first-child input",
      "address 123"
    );

    await click("button.uk-button-primary");

    assert.dom(".uk-card:last-child").hasText("address 123");
  });

  test("it can add a building", async function (assert) {
    assert.expect(4);

    await render(
      hbs`{{camac-gwr 'test-gwr' instance=instance readonly=false}}`
    );

    assert.dom(".uk-card").exists({ count: 2 });

    await click("[data-test-gwr-building-add]");

    assert.dom(".uk-card").exists({ count: 3 });

    await fillIn(
      ".uk-card:last-child .uk-margin:nth-child(1) input",
      "address 123"
    );
    await fillIn(".uk-card:last-child .uk-margin:nth-child(2) input", "123");
    await fillIn(".uk-card:last-child .uk-margin:nth-child(3) input", "1");
    await click(
      ".uk-card:last-child .uk-margin:nth-child(4) label:nth-child(2)"
    );
    await click(
      ".uk-card:last-child .uk-margin:nth-child(4) label:nth-child(3)"
    );

    await click(".uk-card:last-child table tfoot button");
    await fillIn(".uk-modal input", "test");
    await click(".uk-modal button.uk-button-primary");

    await click("button.uk-button-primary");

    assert.dom(".uk-card").exists({ count: 3 });

    assert.dom(".uk-card:first-child").hasText("address 123");
  });

  test("it can delete a building", async function (assert) {
    assert.expect(2);

    await render(
      hbs`{{camac-gwr 'test-gwr' instance=instance readonly=false}}`
    );

    assert.dom(".uk-card").exists({ count: 2 });

    await click(`[data-test-gwr-building=${this.building.value[0].uuid}]`);

    await click(".uk-card-footer button.uk-button-default");

    assert.dom(".uk-card").exists({ count: 1 });
  });
});
