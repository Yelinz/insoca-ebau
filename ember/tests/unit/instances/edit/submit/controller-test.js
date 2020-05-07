import loadQuestions from "citizen-portal/tests/helpers/load-questions";
import { setupMirage } from "ember-cli-mirage/test-support";
import { setupTest } from "ember-qunit";
import { module, test } from "qunit";

module("Unit | Controller | instances/edit/submit", function(hooks) {
  setupTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(async function() {
    const form = this.server.create("form", { name: "test" });

    this.instance = this.server.create("instance", {
      formId: form.id
    });

    this.model = { instance: this.instance, meta: { editable: ["form"] } };

    this.router = { urlFor: () => true };

    this.server.get("/api/v1/form-config", () => ({
      forms: {
        test: ["module"]
      },
      modules: {
        module: {
          questions: ["question-1", "question-2", "question-3"]
        }
      },
      questions: {
        "question-1": {
          type: "text",
          required: true
        },
        "question-2": {
          type: "text",
          required: true
        },
        "question-3": {
          type: "text",
          required: true
        }
      }
    }));

    await loadQuestions(
      ["question-1", "question-2", "question-3"],
      this.instance.id
    );
  });

  test("it computes if the instance can be submitted", async function(assert) {
    assert.expect(2);

    const editController = this.owner.lookup("controller:instances/edit");
    const controller = this.owner.lookup("controller:instances/edit/submit");
    const store = this.owner.lookup("service:question-store");

    editController.setProperties({ model: this.model, router: this.router });
    controller.setProperties({ model: this.model, router: this.router });

    const q1 = await store.peek("question-1", this.instance.id);
    const q2 = await store.peek("question-2", this.instance.id);
    const q3 = await store.peek("question-3", this.instance.id);

    await editController.get("modules").perform();

    await controller.get("canSubmit").perform();
    assert.equal(controller.get("canSubmit.lastSuccessful.value"), false);

    q1.set("model.value", "test");
    q2.set("model.value", "test");
    q3.set("model.value", "test");

    await q1.get("model").save();
    await q2.get("model").save();
    await q3.get("model").save();

    await controller.get("canSubmit").perform();
    assert.equal(controller.get("canSubmit.lastSuccessful.value"), true);
  });
});
