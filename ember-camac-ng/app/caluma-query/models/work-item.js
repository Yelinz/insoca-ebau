import { inject as service } from "@ember/service";
import { tracked } from "@glimmer/tracking";
import { queryManager } from "ember-apollo-client";
import WorkItemModel from "ember-caluma/caluma-query/models/work-item";

import saveWorkItemMutation from "camac-ng/gql/mutations/save-workitem";

export default class CustomWorkItemModel extends WorkItemModel {
  @queryManager apollo;

  @service store;
  @service shoebox;
  @service router;
  @service intl;
  @service notifications;
  @service can;

  @tracked meta = this.raw.meta;
  @tracked notViewed = this.raw.meta["not-viewed"];
  @tracked assignedUsers = this.raw.assignedUsers;
  @tracked addressedGroups = this.raw.addressedGroups;

  get assignedUser() {
    return this.store
      .peekAll("user")
      .find((user) => this.assignedUsers.includes(user.username));
  }

  set assignedUser(user) {
    this.assignedUsers = [user.username];
  }

  get addressedService() {
    if (!parseInt(this.addressedGroups[0])) {
      return {
        name: this.intl.t(`global.${this.addressedGroups[0]}`),
        id: this.addressedGroups[0],
      };
    }

    return this.store
      .peekAll("service")
      .find((service) => this.addressedGroups.includes(service.id));
  }

  get closedByUser() {
    return this.store.peekAll("user").findBy("username", this.raw.closedByUser);
  }

  get createdByUser() {
    return this.store
      .peekAll("user")
      .findBy("username", this.raw.createdByUser);
  }

  get createdByGroup() {
    return (
      this.raw.createdByGroup &&
      this.store.peekRecord("service", this.raw.createdByGroup)
    );
  }

  get isAddressedToCurrentService() {
    return (
      parseInt(this.addressedService?.id) === this.shoebox.content.serviceId
    );
  }

  get isAssignedToCurrentUser() {
    return this.assignedUsers.includes(this.shoebox.content.username);
  }

  get isCreatedByCurrentService() {
    return parseInt(this.createdByGroup?.id) === this.shoebox.content.serviceId;
  }

  get isControlledByCurrentService() {
    return (
      parseInt(this.controllingGroups[0]) === this.shoebox.content.serviceId
    );
  }

  get isReady() {
    return this.raw.status === "READY";
  }

  get isCompleted() {
    return this.raw.status === "COMPLETED";
  }

  get responsible() {
    if (this.isAddressedToCurrentService) {
      return this.assignedUser?.fullName || "-";
    }

    return [
      this.addressedService.name,
      this.assignedUser ? `(${this.assignedUser.fullName})` : "",
    ].join(" ");
  }

  get case() {
    return this.raw.case.parentWorkItem?.case || this.raw.case;
  }

  get instanceId() {
    return this.case?.meta["camac-instance-id"];
  }

  get instance() {
    return this.store.peekRecord("instance", this.instanceId);
  }

  get instanceName() {
    const identifier = this.instance?.identifier || this.instanceId;
    const name = this.instance?.name || this.instance?.form.get("description");
    const ebauNr = this.case?.meta["ebau-number"];
    const suffix = ebauNr ? `(${ebauNr})` : "";

    if (name) {
      return `${identifier} - ${name} ${suffix}`.trim();
    }

    return identifier;
  }

  get instanceDescription() {
    if (this.shoebox.content.application === "kt_schwyz") {
      const { value } = this.store
        .peekAll("form-field")
        .find(
          (field) =>
            field.instance.get("id") === this.instanceId.toString() &&
            field.name === "bezeichnung"
        );

      return value;
    }

    return this.case?.document.answers.edges
      .map((edge) => edge.node.value)
      .join("\n");
  }

  get directLink() {
    if (this.can.cannot("edit work-item", this)) return null;

    return this._getDirectLinkFor(this.raw.task.slug) || this.editLink;
  }

  get editLink() {
    const url = this._getDirectLinkFor("edit");
    const hash = this.router.urlFor(
      "work-items.instance.edit",
      this.instanceId,
      this.id
    );

    return this.can.can("edit work-item", this) && url && `${url}${hash}`;
  }

  _getDirectLinkFor(configKey) {
    try {
      const config = this.shoebox.content.config.directLink;
      const role = this.shoebox.role;

      const template = config[configKey][role];
      const data = {
        INSTANCE_ID: this.instanceId,
        CIRCULATION_ID: this.raw.meta["circulation-id"],
        ACTIVATION_ID: this.raw.meta["activation-id"],
      };

      return Object.entries(data).reduce(
        (str, [key, value]) => str.replace(`{{${key}}}`, value),
        template
      );
    } catch (error) {
      return null;
    }
  }

  async toggleRead() {
    try {
      this.notViewed = !this.notViewed;

      await this.apollo.mutate({
        mutation: saveWorkItemMutation,
        variables: {
          input: {
            workItem: this.id,
            meta: JSON.stringify({
              ...this.raw.meta,
              "not-viewed": this.notViewed,
            }),
          },
        },
      });

      return true;
    } catch (error) {
      this.notifications.error(this.intl.t("workItems.saveError"));
    }
  }

  async assignToMe() {
    const id = this.shoebox.content.userId;
    const user =
      (await this.store.peekRecord("user", id)) ||
      (await this.store.findRecord("user", id, { reload: true }));

    return await this.assignToUser(user);
  }

  async assignToUser(user) {
    try {
      this.assignedUser = user;

      await this.apollo.mutate({
        mutation: saveWorkItemMutation,
        variables: {
          input: {
            workItem: this.id,
            assignedUsers: this.assignedUsers,
          },
        },
      });

      return true;
    } catch (error) {
      this.notifications.error(this.intl.t("workItems.saveError"));
    }
  }

  static fragment = `{
    createdAt
    createdByUser
    createdByGroup
    closedAt
    closedByUser
    closedByGroup
    status
    meta
    addressedGroups
    controllingGroups
    assignedUsers
    name
    deadline
    description
    case {
      id
      meta
      document {
        form {
          name
        }
        answers(questions: ["anfrage-zur-vorabklaerung", "beschreibung-bauvorhaben"]) {
          edges {
            node {
              ... on StringAnswer {
                value
              }
            }
          }
        }
      }
      parentWorkItem {
        case {
          meta
          document {
            form {
              name
            }
            answers(questions: ["anfrage-zur-vorabklaerung", "beschreibung-bauvorhaben"]) {
              edges {
                node {
                  ... on StringAnswer {
                    value
                  }
                }
              }
            }
          }
        }
      }
    }
    task {
      slug
      meta
    }
  }`;
}
