import { run } from "@ember/runloop";
import { settled } from "@ember/test-helpers";
import loadQuestions from "citizen-portal/tests/helpers/load-questions";
import { setupMirage } from "ember-cli-mirage/test-support";
import { setupTest } from "ember-qunit";
import { module, test } from "qunit";

module("Unit | Service | question-store", function(hooks) {
  setupTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(function() {
    const { id } = this.server.create("instance");

    this.instanceId = id;

    this.server.get("/api/v1/form-config", () => ({
      questions: {}
    }));
  });

  test("can build a question without model", async function(assert) {
    assert.expect(4);

    const service = this.owner.lookup("service:question-store");

    const question = await service.buildQuestion("test", this.instanceId);

    assert.ok(question.get("name"));
    assert.ok(question.get("field"));
    assert.ok(question.get("model"));
    assert.ok(question.get("model.isNew"));
  });

  test("can build a question with model", async function(assert) {
    assert.expect(4);

    this.server.create("form-field", {
      name: "test",
      instanceId: this.instanceId
    });

    const service = this.owner.lookup("service:question-store");
    const store = this.owner.lookup("service:store");

    const model = await run(
      async () =>
        await store.query("form-field", { name: "test", include: "instance" })
    );

    const question = await service.buildQuestion(
      "test",
      this.instanceId,
      model.firstObject
    );

    assert.ok(question.get("name"));
    assert.ok(question.get("field"));
    assert.ok(question.get("model"));
    assert.notOk(question.get("model.isNew"));
  });

  test("can validate question", async function(assert) {
    assert.expect(2);

    this.server.get("/api/v1/form-config", () => ({
      questions: {
        test1: {
          type: "text",
          required: true
        },
        test2: {
          type: "text",
          required: true
        }
      }
    }));

    const service = this.owner.lookup("service:question-store");

    await loadQuestions(["test1", "test2"], this.instanceId);

    const validations = {
      test1(_, value) {
        return `${value} is an invalid value!`;
      },
      test2(_, value) {
        return value === "somevalue";
      }
    };

    service.set("_validations", validations);

    const test1 = await service.peek("test1", this.instanceId);
    const test2 = await service.peek("test2", this.instanceId);

    test1.set("model.value", "somevalue");
    test2.set("model.value", "somevalue");

    assert.equal(test1.validate(), "somevalue is an invalid value!");
    assert.equal(test2.validate(), true);
  });

  test("can handle active expressions", async function(assert) {
    assert.expect(4);

    this.server.get("/api/v1/form-config", {
      questions: {
        test: {
          "active-expression": "'foo'|value in [1,2] || !('bar'|value > 2)"
        },
        "test-map": {
          "active-expression": "'test' in [{name:'test'}]|mapby('name')"
        }
      }
    });

    await loadQuestions(["test", "test-map", "foo", "bar"], this.instanceId);

    const service = this.owner.lookup("service:question-store");

    const test = await service.peek("test", this.instanceId);
    const foo = await service.peek("foo", this.instanceId);
    const bar = await service.peek("bar", this.instanceId);

    const testMap = await service.peek("test-map", this.instanceId);
    await testMap.get("_hiddenTask").perform();
    assert.equal(testMap.get("hidden"), false);

    foo.set("model.value", 3);
    bar.set("model.value", 3);
    await test.get("_hiddenTask").perform();
    assert.equal(
      test.get("hidden"),
      true,
      "The values of foo (3) AND bar (3) do not meet the expression"
    );

    foo.set("model.value", 2);
    await test.get("_hiddenTask").perform();
    assert.equal(
      test.get("hidden"),
      false,
      "The values of foo (2) meets the expression but bar (1) does not"
    );

    bar.set("model.value", 1);
    await test.get("_hiddenTask").perform();
    assert.equal(
      test.get("hidden"),
      false,
      "The values of foo (3) AND bar (1) meet the expression"
    );
  });

  test("can save a question", async function(assert) {
    assert.expect(6);

    this.server.get("/api/v1/form-config", {
      questions: {
        test: {
          type: "number",
          required: true
        }
      }
    });

    const service = this.owner.lookup("service:question-store");

    await loadQuestions(["test"], this.instanceId);

    const question = service.peek("test", this.instanceId);

    assert.deepEqual(await service.get("saveQuestion").perform(question), [
      "Diese Frage darf nicht leer gelassen werden"
    ]);
    assert.equal(question.get("model.isNew"), true);

    question.set("model.value", "test");
    assert.deepEqual(await service.get("saveQuestion").perform(question), [
      "Der Wert muss eine Zahl sein"
    ]);
    assert.equal(question.get("model.isNew"), true);

    question.set("model.value", 5);
    assert.deepEqual(await service.get("saveQuestion").perform(question), null);
    assert.equal(question.get("model.isNew"), false);
  });

  test("can handle hierarchical active expressions", async function(assert) {
    assert.expect(6);

    this.server.get("/api/v1/form-config", {
      questions: {
        test1: {},
        test2: {
          "active-expression": "'test1'|value == 'test1'"
        },
        test3: {
          "active-expression": "'test2'|value == 'test2'"
        }
      }
    });

    await loadQuestions(["test1", "test2", "test3"], this.instanceId);

    const service = this.owner.lookup("service:question-store");

    const test1 = await service.peek("test1", this.instanceId);
    const test2 = await service.peek("test2", this.instanceId);
    const test3 = await service.peek("test3", this.instanceId);

    test1.set("model.value", "xyz");
    test2.set("model.value", "xyz");
    test3.set("model.value", "xyz");
    await settled();
    await test2._hiddenTask.perform();
    await test3._hiddenTask.perform();

    assert.equal(test2.get("hidden"), true);
    assert.equal(test3.get("hidden"), true);

    test2.set("model.value", "test2");
    await settled();
    await test2._hiddenTask.perform();

    assert.equal(test2.get("hidden"), true);
    assert.equal(test3.get("hidden"), true);

    test1.set("model.value", "test1");
    test2.set("model.value", "test2");
    await settled();
    await test2._hiddenTask.perform();
    await test3._hiddenTask.perform();

    assert.equal(test2.get("hidden"), false);
    assert.equal(test3.get("hidden"), false);
  });
});
