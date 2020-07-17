import { visit, currentURL, click, fillIn } from "@ember/test-helpers";
import { setupMirage } from "ember-cli-mirage/test-support";
import { setupApplicationTest } from "ember-qunit";
import { authenticateSession } from "ember-simple-auth/test-support";
import { module, test } from "qunit";

module("Acceptance | instance list", function (hooks) {
  setupApplicationTest(hooks);
  setupMirage(hooks);

  hooks.beforeEach(async function () {
    await authenticateSession();
  });

  test("has correct empty state", async function (assert) {
    assert.expect(4);

    await visit("/gesuche");

    assert.dom("svg").exists();
    assert.dom("h4").hasText("Sie haben noch keine Gesuche!");
    assert.dom(".uk-button-primary").exists();

    await click(".uk-button-primary");

    assert.equal(currentURL(), "/gesuche/new");
  });

  test("has correct default state", async function (assert) {
    assert.expect(2);

    this.server.createList("instance", 5);

    await visit("/gesuche");

    // Should have 5 data rows and one to add a new row
    assert.dom("table > tbody > tr").exists({ count: 6 });

    await click("table > tbody > tr:last-of-type");

    assert.equal(currentURL(), "/gesuche/new");
  });

  test("can sort and search for identifier", async function (assert) {
    assert.expect(3);

    this.server.createList("instance", 5);

    await visit("/gesuche");

    assert.equal(currentURL(), "/gesuche");

    await click("a.uk-search-icon.uk-toggle");
    await fillIn("input.uk-search-input", "123");

    assert.ok(/(\?|&)identifier=123/.test(currentURL()));

    await click("table > thead > tr > th:nth-of-type(7) > span.pointer");

    assert.ok(/(\?|&)sort=creation_date/.test(currentURL()));
  });

  test("can delete non submitted instance", async function (assert) {
    assert.expect(3);

    this.server.createList("instance", 2, "unsubmitted");

    await visit("/gesuche");

    // Two instance rows and one "add instance" row
    assert.dom("table > tbody > tr").exists({ count: 3 });

    await click("table > tbody > tr > td:last-of-type > button");

    assert
      .dom("table > tbody > tr:first-of-type > td:last-of-type > span")
      .hasText("Löschen?");

    await click(
      "table > tbody > tr:first-of-type > td:last-of-type > span > button:first-of-type"
    );

    // One instance row and one "add instance" row
    assert.dom("table > tbody > tr").exists({ count: 2 });
  });
});
