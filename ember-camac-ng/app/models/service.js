import Model, { attr } from "@ember-data/model";

export default class ServiceModel extends Model {
  @attr("string") name;
  @attr("string") description;
  @attr("string") phone;
  @attr("string") zip;
  @attr("string") city;
  @attr("string") address;
  @attr("string") email;
  @attr("string") website;
}
