import { inject as service } from "@ember/service";
import { tracked } from "@glimmer/tracking";
import WorkItemModel from "ember-caluma/caluma-query/models/work-item";
import moment from "moment";

export default class CustomWorkItemModel extends WorkItemModel {
  @service store;

  @tracked notViewed = this.raw.meta["not-viewed"];
  @tracked assignedUsers = this.raw.assignedUsers;
  @tracked addressedGroups = this.raw.addressedGroups;

  get assignedUserInformation() {
    return this.store
      .peekAll("user")
      .filter(user => this.assignedUsers.includes(user.username));
  }

  get addressedServices() {
    return this.store
      .peekAll("service")
      .filter(service => this.addressedGroups.includes(service.id));
  }

  get instance() {
    return this.store.peekRecord("instance", this.instanceId);
  }

  get instanceIdentifier() {
    const szIdentifier = this.instance?.identifier;

    const ebauNr = this.case?.meta["ebau-number"];
    const beIdentifier = ebauNr
      ? `${this.instanceId} (${ebauNr})`
      : this.instanceId;

    return szIdentifier || beIdentifier;
  }

  get case() {
    return this.raw.case.parentWorkItem?.case || this.raw.case;
  }

  get instanceId() {
    return this.case?.meta["camac-instance-id"];
  }

  get instanceName() {
    return this.instance?.name || this.case.document.form.name;
  }

  get instanceLink() {
    return `/index/redirect-to-instance-resource/instance-id/${this.instanceId}`;
  }

  get workItemColor() {
    const remainingDays = moment(this.raw.deadline).diff(moment(), "days");

    if (remainingDays <= 0) {
      return "expired";
    } else if (remainingDays <= 3) {
      return "expiring";
    }

    if (this.notViewed) {
      return "not-viewed";
    }

    return "";
  }

  get closedByUser() {
    return this.store.peekAll("user").findBy("username", this.raw.closedByUser);
  }

  get createdByUser() {
    return this.store
      .peekAll("user")
      .findBy("username", this.raw.createdByUser);
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
      }
      parentWorkItem {
        case {
          meta
          document {
            form {
              name
            }
          }
        }
      }
    }
    task {
      slug
    }
  }`;
}
