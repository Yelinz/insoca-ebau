import Controller from "@ember/controller";
import { inject as service } from "@ember/service";
import { inject as controller } from "@ember/controller";
import { reads } from "@ember/object/computed";
import { computed } from "@ember/object";
import { task } from "ember-concurrency";
import { getOwner } from "@ember/application";
import { decodeId } from "ember-caluma/helpers/decode-id";

import Attachment from "ember-caluma-portal/lib/attachment";

const EDITABLE_INSTANCE_STATE_NAMES = ["Neu", "Zurückgewiesen"];
const FEEDBACK_ATTACHMENT_SECTION = 3;

const FeedbackAttachment = Attachment.extend({
  calumaStore: service(),

  document: computed(
    "calumaStore.hash.document.[]",
    "documentUuid",
    function() {
      return this.calumaStore.find(`Document:${this.documentUuid}`);
    }
  )
});

export default Controller.extend({
  fetch: service(),

  editController: controller("instances.edit"),
  data: reads("editController.data"),
  instanceState: reads("editController.instanceState"),
  case: reads("data.lastSuccessful.value"),

  disabled: computed("instanceState.lastSuccessful.value", function() {
    return !EDITABLE_INSTANCE_STATE_NAMES.includes(
      this.get("instanceState.lastSuccessful.value.attributes.name")
    );
  }),

  feedbackData: task(function*() {
    const response = yield this.fetch.fetch(
      `/api/v1/attachments?attachment_sections=${FEEDBACK_ATTACHMENT_SECTION}&instance=${this.model}`
    );

    const {
      document: { id: documentId }
    } = yield this.data.last;

    const { data } = yield response.json();

    return data.map(attachment =>
      FeedbackAttachment.create(
        getOwner(this).ownerInjection(),
        Object.assign(attachment, {
          documentUuid: decodeId(documentId)
        })
      )
    );
  }).restartable()
});
