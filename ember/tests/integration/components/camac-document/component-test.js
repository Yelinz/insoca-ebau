import { module, test } from "qunit";
import { setupRenderingTest } from "ember-qunit";
import { render, find, triggerEvent, click } from "@ember/test-helpers";
import hbs from "htmlbars-inline-precompile";
import setupMirage from "ember-cli-mirage/test-support/setup-mirage";
import loadQuestions from "citizen-portal/tests/helpers/load-questions";

module("Integration | Component | camac-document", function(hooks) {
  setupRenderingTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(async function() {
    let instance = this.server.create("instance", "unsubmitted");

    this.set("instance", instance);

    this.server.createList("attachment", 2, {
      name: "foo",
      question: "test-document",
      instance
    });

    this.server.create("attachment", {
      name: "bar",
      question: "test-document",
      instance
    });

    this.server.get("/api/v1/form-config", () => {
      return {
        questions: {
          "test-document": {
            label: "Test Doc",
            hint: "Hint hint hint",
            type: "document",
            required: true,
            config: {}
          }
        }
      };
    });

    await loadQuestions(["test-document"], instance.id);
  });

  test("it renders", async function(assert) {
    assert.expect(1);

    await render(hbs`{{camac-document 'test-document' instance=instance}}`);

    assert.dom(".uk-card-header").hasText("Test Doc *");
  });

  test("it can upload a document", async function(assert) {
    assert.expect(2);

    this.server.post("/api/v1/attachments", ({ attachments }) => {
      assert.step("upload-document");

      return attachments.first();
    });

    await render(hbs`{{camac-document 'test-document'instance=instance}}`);

    let files = [new File([new Blob()], "testfile.png", { type: "image/png" })];
    let input = await find("[data-test-upload-document] + input[type=file");

    input.files.item = i => {
      return files[i];
    };

    await triggerEvent(
      "[data-test-upload-document] + input[type=file]",
      "change"
    );

    assert.verifySteps(["upload-document"]);
  });

  test("it can replace a document", async function(assert) {
    assert.expect(3);

    this.server.patch(
      "/api/v1/attachments/:id",
      ({ attachments }, { requestBody }) => {
        assert.step("upload-document");

        assert.equal(requestBody.get("path").name, "bar");

        return attachments.first();
      }
    );

    await render(hbs`{{camac-document 'test-document'instance=instance}}`);

    let files = [new File([new Blob()], "testfile.png", { type: "image/png" })];
    let input = await find("[data-test-replace-document] + input[type=file");

    input.files.item = i => {
      return files[i];
    };

    await triggerEvent(
      "[data-test-replace-document] + input[type=file]",
      "change"
    );

    assert.verifySteps(["upload-document"]);
  });

  test("it can download a document", async function(assert) {
    assert.expect(2);

    this.server.get("/api/v1/attachments/:id/files/:name", () => {
      assert.step("download-document");

      return new Blob();
    });

    await render(hbs`{{camac-document 'test-document'instance=instance}}`);

    await click("[data-test-download-document]");

    assert.verifySteps(["download-document"]);
  });

  test("it can delete a document", async function(assert) {
    assert.expect(2);

    this.server.delete("/api/v1/attachments/:id", () => {
      assert.step("delete-document");

      return {};
    });

    await render(hbs`{{camac-document 'test-document' instance=instance}}`);

    await click("[data-test-delete-document]");
    await click("[data-test-delete-document-confirm]");

    assert.verifySteps(["delete-document"]);
  });

  // If instance has never been submitted delete button is displayed
  test("delete document button is not visible", async function(assert) {
    const instanceState = this.server.create("instance-state", { name: "new" });

    let n = String(this.instance.location.communalFederalNumber).substr(2, 4);
    let y = String(new Date().getFullYear()).substr(2, 4);
    let i = String(this.instance.id).padStart(3, 0);

    // Set instance to submitted
    this.set("instance.identifier", `${n}-${y}-${i}`);
    this.set("instance.instanceState", instanceState);

    await loadQuestions(["test-document"], this.instance.id);

    await render(hbs`{{camac-document 'test-document' instance=instance}}`);

    assert.notOk(await find("[data-test-delete-document]"));
  });
});
