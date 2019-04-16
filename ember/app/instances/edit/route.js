import Route from "@ember/routing/route";
import { inject as service } from "@ember/service";
import { all } from "rsvp";

export default Route.extend({
  ajax: service(),
  questionStore: service(),

  queryParams: {
    group: { refreshModel: true }
  },

  async model({ instance_id: id, group }) {
    let response = await this.ajax.request(`/api/v1/instances/${id}`, {
      data: {
        group,
        include: "form,instance_state,location"
      },
      headers: {
        Accept: "application/vnd.api+json"
      }
    });

    await this.store.query("form-field", { instance: id, group });
    await this.store.query("attachment", {
      instance: id,
      group,
      include: "attachment-sections"
    });

    let {
      data: { meta }
    } = response;

    this.store.pushPayload(response);

    return {
      instance: this.store.peekRecord("instance", id),
      meta
    };
  },

  async afterModel(model) {
    let { forms, modules } = await this.questionStore.config;

    let questions = [
      ...new Set(
        forms[model.instance.get("form.name")].reduce((qs, mod) => {
          return [...qs, ...modules[mod].questions];
        }, [])
      )
    ];

    let build = name =>
      this.questionStore.buildQuestion(name, model.instance.id);

    let questionObjects = await all(questions.map(await build));

    this.questionStore._store.pushObjects(questionObjects);
  },

  resetController(_, isExiting) {
    if (isExiting) {
      // We clear the store and the question store at this point so we do not
      // have too much unnecessary data in the memory
      this.store.unloadAll();
      this.questionStore.clear();
    }
  }
});
