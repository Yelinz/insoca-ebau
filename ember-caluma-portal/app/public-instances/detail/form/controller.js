import Controller, { inject as controller } from "@ember/controller";

export default class PublicInstancesDetailFormController extends Controller {
  queryParams = ["displayedForm"];

  @controller("public-instances.detail") detailController;

  get documentId() {
    return this.detailController.publicInstance?.documentId;
  }
}
