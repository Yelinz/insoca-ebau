import { assert } from "@ember/debug";
import { later, cancel } from "@ember/runloop";
import { inject as service } from "@ember/service";
import BaseAuthenticator from "ember-simple-auth/authenticators/base";
import fetch from "fetch";

const TOKEN_REFRESH_LEEWAY = 30 * 1000; // 30 seconds

export default class CamacAuthenticator extends BaseAuthenticator {
  @service shoebox;

  restore() {
    assert(
      "Token can't be restored since we don't have a persistent session store"
    );
  }

  async authenticate() {
    const token = this.shoebox.content.token;

    assert("No token passed in shoebox", token);

    return this.handleToken(token);
  }

  async refresh() {
    const token = await fetch("/index/token", {
      credentials: "same-origin"
    }).then(response => response.text());

    return this.handleToken(token);
  }

  handleToken(token) {
    const [, body] = token.split(".");
    const { exp } = JSON.parse(decodeURIComponent(escape(atob(body))));

    const diff = new Date(exp * 1000) - new Date() - TOKEN_REFRESH_LEEWAY;

    if (diff > 0) {
      cancel(this._timer);
      this._timer = later(this, "refresh", diff);
    } else {
      this.refresh();
    }

    return { token, exp };
  }
}
