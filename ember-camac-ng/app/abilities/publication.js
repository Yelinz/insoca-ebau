import { inject as service } from "@ember/service";
import { Ability } from "ember-can";

export default class PublicationAbility extends Ability {
  @service shoebox;

  get canEdit() {
    return (
      this.shoebox.role === "municipality" &&
      !this.shoebox.isReadOnlyRole &&
      this.model?.status === "READY"
    );
  }

  get canCreate() {
    return this.shoebox.role === "municipality" && !this.shoebox.isReadOnlyRole;
  }
}
