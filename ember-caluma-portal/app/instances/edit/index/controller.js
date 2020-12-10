import Controller, { inject as controller } from "@ember/controller";
import { reads } from "@ember/object/computed";
import { inject as service } from "@ember/service";
import { queryManager } from "ember-apollo-client";
import { dropTask, lastValue } from "ember-concurrency-decorators";
import UIkit from "uikit";

import config from "../../../config/environment";

import getOverviewCaseQuery from "ember-caluma-portal/gql/queries/get-overview-case";

const findAnswer = (answers, slug) => {
  const answer = answers.find((answer) => answer.question.slug === slug);

  if (!answer) {
    return null;
  }

  const key = Object.keys(answer).find((key) => /Value$/.test(key));

  return answer[key];
};

function getAddress(answers) {
  const street =
    findAnswer(answers, "strasse-flurname") ||
    findAnswer(answers, "strasse-gesuchstellerin");

  const number =
    findAnswer(answers, "nr") || findAnswer(answers, "nummer-gesuchstellerin");

  const city =
    findAnswer(answers, "ort-grundstueck") ||
    findAnswer(answers, "ort-gesuchstellerin");

  return [[street, number].filter(Boolean).join(" "), city]
    .filter(Boolean)
    .join(", ");
}

function getEbauNr(raw) {
  return raw.meta["ebau-number"];
}

function getType(raw) {
  return raw.document.form.name;
}

function getMunicipality(answers) {
  const answer = answers.find((answer) => answer.question.slug === "gemeinde");
  const selectedOption =
    answer &&
    answer.question.options.edges.find((option) => {
      return answer.stringValue === option.node.slug;
    });

  return selectedOption && selectedOption.node.label;
}

function getBuildingSpecification(answers) {
  return (
    findAnswer(answers, "beschreibung-bauvorhaben") ||
    findAnswer(answers, "anfrage-zur-vorabklaerung")
  );
}

export default class InstancesEditIndexController extends Controller {
  @queryManager apollo;
  @service fetch;
  @service notification;
  @service intl;

  @controller("instances.edit") editController;
  @reads("editController.feedbackTask.isRunning") feedbackLoading;
  @reads("editController.decisionTask.isRunning") decisionLoading;
  @reads("editController.feedback") feedback;
  @reads("editController.decision") decision;
  @reads("editController.instance") instance;

  get isRejection() {
    return (
      parseInt(this.get("instance.instanceState.id")) ===
      config.ebau.instanceStates.rejected
    );
  }

  @lastValue("dataTask") data;
  @dropTask
  *dataTask() {
    const raw = yield this.apollo.query(
      {
        fetchPolicy: "network-only",
        query: getOverviewCaseQuery,
        variables: {
          instanceId: this.model,
        },
      },
      "allCases.edges.firstObject.node"
    );
    const answers = raw.document.answers.edges.map(({ node }) => node);

    return {
      address: getAddress(answers),
      ebauNr: getEbauNr(raw),
      type: getType(raw),
      municipality: getMunicipality(answers),
      buildingSpecification: getBuildingSpecification(answers),
    };
  }

  @dropTask
  *createModification() {
    yield this.copy.perform(true);
  }

  @dropTask
  *createCopy() {
    yield this.copy.perform();
  }

  @dropTask
  *copy(isModification = false) {
    const response = yield this.fetch.fetch(`/api/v1/instances`, {
      method: "POST",
      body: JSON.stringify({
        data: {
          attributes: {
            "copy-source": this.model,
            "is-modification": isModification,
          },
          type: "instances",
        },
      }),
    });

    const { data } = yield response.json();

    yield this.transitionToRoute(
      "instances.edit.form",
      data.id,
      this.instance.calumaForm
    );
  }

  @dropTask
  *deleteInstance() {
    try {
      yield UIkit.modal.confirm(this.intl.t("instances.deleteInstanceModal"), {
        labels: {
          ok: this.intl.t("global.ok"),
          cancel: this.intl.t("global.cancel"),
        },
      });
    } catch (error) {
      return;
    }

    try {
      yield this.instance.destroyRecord();
      this.notification.success(this.intl.t("instances.deleteInstanceSuccess"));
      yield this.transitionToRoute("instances");
    } catch (error) {
      this.notification.danger(this.intl.t("instances.deleteInstanceError"));
    }
  }

  @dropTask
  *createNewFormExtensionPeriodOfValidity() {
    const response = yield this.fetch.fetch(`/api/v1/instances`, {
      method: "POST",
      body: JSON.stringify({
        data: {
          attributes: {
            "caluma-form": "verlaengerung-geltungsdauer",
            "extend-validity-for": this.instance.id,
          },
          type: "instances",
        },
      }),
    });

    const {
      data: { id: instanceId },
    } = yield response.json();

    yield this.transitionToRoute(
      "instances.edit.form",
      instanceId,
      "verlaengerung-geltungsdauer"
    );
  }
}
