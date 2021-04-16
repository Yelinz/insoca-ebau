import { getOwner } from "@ember/application";
import Controller from "@ember/controller";
import EmberObject, { computed, get } from "@ember/object";
import { gt } from "@ember/object/computed";
import { inject as service } from "@ember/service";
import { tracked } from "@glimmer/tracking";
import computedTask from "citizen-portal/lib/computed-task";
import { task } from "ember-concurrency-decorators";

class Module extends EmberObject {
  @service questionStore;

  queryParams = ["group"];
  @tracked group = null;

  @computed("questions", "submodules.@each.questions")
  get allQuestions() {
    return [
      ...(this.questions || []),
      ...(this.submodules || []).reduce((qs, submodule) => {
        return [...qs, ...(submodule.questions || [])];
      }, []),
    ];
  }

  @computed("editableTypes.[]", "isApplicant")
  get editable() {
    if (!this.isApplicant) {
      return false;
    }

    const questions = this.questionStore.peekSet(
      this.allQuestions || [],
      this.instance
    );
    const editable = this.editableTypes || [];

    const editableFieldTypes = [
      ...(editable.includes("form")
        ? ["text", "number", "radio", "checkbox", "table", "gwr"]
        : []),
      ...(editable.includes("document") ? ["document"] : []),
    ];

    return questions.some(({ field: { type } }) => {
      return editableFieldTypes.includes(type);
    });
  }

  @computed("questionStore._store.@each.{value,hidden,isNew}")
  get state() {
    const names = this.allQuestions || [];

    const questions = this.questionStore
      .peekSet(names, this.instance)
      .filter((q) => !q.hidden);

    if (!questions.length) {
      return null;
    }

    if (questions.every((q) => q.get("isNew"))) {
      return "untouched";
    }

    const relevantQuestions = questions.filter((q) => q.get("field.required"));

    if (relevantQuestions.some((q) => q.get("isNew"))) {
      return "unfinished";
    }

    return relevantQuestions.every((q) => q.validate() === true)
      ? "valid"
      : "invalid";
  }
}

export default class InstancesEditController extends Controller {
  @service questionStore;
  @service router;
  @service ajax;

  @computedTask("_modules", "model.instance.form.name")
  modules;

  @task
  *_modules() {
    const { forms, modules } = yield this.get("questionStore.config");

    const usedModules = (forms[this.get("model.instance.form.name")] || [])
      .map((name) => ({ name, ...modules[name] } || null))
      .filter(Boolean);

    return usedModules
      .map(({ name, title, parent, questions }) => {
        return Module.create({
          container: getOwner(this).__container__,

          link: `instances.edit.${name}`,
          instance: this.get("model.instance.id"),
          editableTypes: this.get("model.meta.editable"),
          isApplicant: this.get("model.meta.access-type") === "applicant",
          name,
          title,
          questions,
          parent,
          submodules: [],
        });
      })
      .filter((mod) => {
        try {
          this.router.urlFor(mod.get("link"));
          return true;
        } catch (e) {
          // URL does not exist, skip this module
          return false;
        }
      });
  }

  @computed("modules.lastSuccessful.value.[]")
  get navigation() {
    return (this.modules.lastSuccessful?.value || []).reduce((nav, mod) => {
      if (mod.get("parent")) {
        const parent = nav.find((n) => n.get("name") === mod.get("parent"));

        parent.set("submodules", [
          ...parent
            .get("submodules")
            .filter((sub) => sub.get("name") !== mod.get("name")),
          mod,
        ]);
      } else if (
        !this.get("model.meta.access-type") &&
        mod.get("name") !== "gesuchsunterlagen"
      ) {
        nav.push(mod);
      } else {
        nav.push(mod);
      }

      return nav;
    }, []);
  }

  @computed(
    "modules.lastSuccessful.value.[]",
    "questionStore._store.@each.{value,isNew,hidden}"
  )
  get links() {
    const editableTypes = ["form", "document"];
    return [
      "instances.edit.index",
      ...(this.modules.lastSuccessful?.value || [])
        .filter(({ state }) => Boolean(state))
        .mapBy("link"),
      ...(this.get("model.meta.editable").some((e) => editableTypes.includes(e))
        ? ["instances.edit.submit"]
        : []),
    ];
  }

  @computed("links.[]", "router.currentRouteName")
  get currentIndex() {
    return (this.links || []).indexOf(this.get("router.currentRouteName"));
  }

  @gt("currentIndex", 0) hasPrev;
  @computed("links.length", "currentIndex.lastSuccessful.value")
  get hasNext() {
    return this.currentIndex < (this.links.length || 0) - 1;
  }

  @computed("router.currentRouteName")
  get currentPage() {
    switch (this.get("router.currentRouteName")) {
      case "instances.edit.involvierte-personen":
        return "applicants";
      case "instances.edit.freigegebene-unterlagen":
        return "documents";
      case "instances.edit.publikationsdokumente":
        return "documents";
      case "instances.edit.work-items.index":
        return "work-items";
      case "instances.edit.work-items.detail":
        return "work-items";
      default:
        return "form";
    }
  }

  @task
  *prev() {
    yield this.get("questionStore.saveQuestion.last");

    const links = this.links;
    const i = this.currentIndex;

    yield this.transitionToRoute(
      get(links, (i + links.length - 1) % links.length)
    );
  }

  @task
  *next() {
    yield this.get("questionStore.saveQuestion.last");

    const links = this.links;
    const i = this.currentIndex;

    yield this.transitionToRoute(get(links, (i + 1) % links.length));
  }

  get instanceTransformation() {
    const meta = this.questionStore.peek("meta", this.model.instance.id);
    if (meta?.value) {
      const formId = JSON.parse(meta.value).formChange.id;
      if (formId) {
        const form = this.store.findRecord("form", formId);
        return form.description;
      }
    }
    return null;
  }
}
