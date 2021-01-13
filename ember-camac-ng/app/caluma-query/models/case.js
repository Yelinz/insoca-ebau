import { inject as service } from "@ember/service";
import CaseModel from "ember-caluma/caluma-query/models/case";
import moment from "moment";

const instanceResourceDocumentMapping = {
  6: 46, // Sekretariat der Gemeindebaubehörde
  1104: 770, // Vernehmlassungsstelle Gemeindezirkulation
  4: 525, // Vernehmlassungsstelle mit Koordinationsaufgaben
  1021: 525, // Vernehmlassungsstelle ohne Koordinationsaufgaben
  1: 676, // Guest
  1101: 607, // Koordinationsstelle Baudirektion BD
  3: 145, // Koordinationsstelle Baugesuche BG
  1127: 725, // Koordinationsstelle Energie AfE
  1128: 737, // Koordinationsstelle Forst und Jagd AFJ
  1107: 716, // Koordinationsstelle Landwirtschaft ALA
  1061: 466, // Koordinationsstelle Nutzungsplanung NP
  1129: 737, // Koordinationsstelle Sicherheitsdirektion SD
  1106: 701, // Koordinationsstelle Umweltschutz AfU
};

function getAnswer(document, slug) {
  return document.answers.edges.find(
    (edge) => edge.node.question.slug === slug
  );
}

export default class CustomCaseModel extends CaseModel {
  @service store;
  @service shoebox;

  getPersonData(question) {
    const answer = getAnswer(this.raw.document, question);
    // Take the first row and use this as applicant
    const tableAnswers = answer?.node.value[0];

    if (tableAnswers) {
      return {
        firstName: getAnswer(tableAnswers, "first-name")?.node.stringValue,
        lastName: getAnswer(tableAnswers, "last-name")?.node.stringValue,
        street: getAnswer(tableAnswers, "street")?.node.stringValue,
        streetNumber: getAnswer(tableAnswers, "street-number")?.node
          .stringValue,
        zip: getAnswer(tableAnswers, "zip")?.node.stringValue,
        city: getAnswer(tableAnswers, "city")?.node.stringValue,
        phone: getAnswer(tableAnswers, "phone")?.node.stringValue,
        email: getAnswer(tableAnswers, "e-mail")?.node.stringValue,
        juristicName: getAnswer(tableAnswers, "juristic-person-name")?.node
          .stringValue,

        get name() {
          return [
            this.juristicName,
            `${this.firstName ?? ""} ${this.lastName ?? ""}`,
          ]
            .filter(Boolean)
            .join(", ");
        },
      };
    }
    return null;
  }

  get instanceId() {
    return this.raw.meta["camac-instance-id"];
  }

  get instance() {
    return this.store.peekRecord("instance", this.instanceId);
  }

  get user() {
    // TODO camac_legacy read user from caluma
    return this.instance?.get("user.username");
  }

  get street() {
    const street =
      getAnswer(this.raw.document, "parcel-street")?.node.stringValue ?? "";
    const number =
      getAnswer(this.raw.document, "street-number")?.node.stringValue ?? "";

    return `${street} ${number}`;
  }

  get parcelPictureUrl() {
    return `/documents/list/download/instance-resource-id/${
      instanceResourceDocumentMapping[this.shoebox.content.roleId]
    }/instance-id/${this.instanceId}/attachmentid/`;
  }

  get intent() {
    return getAnswer(this.raw.document, "proposal-description")?.node
      .stringValue;
  }

  get authority() {
    const authorityId = getAnswer(this.raw.document, "leitbehoerde")?.node
      .stringValue;

    return this.store.findRecord("authority", Number(authorityId));
  }

  get dossierNr() {
    return this.raw.meta["dossier-number"];
  }

  get municipality() {
    // TODO camac_legacy: Is the municipality in caluma actually set in camac?
    return getAnswer(this.raw.document, "municipality")?.node.stringValue;
  }

  get applicant() {
    return this.getPersonData("applicant");
  }

  get projectAuthor() {
    return this.getPersonData("project-author");
  }

  get landowner() {
    return this.getPersonData("landowner");
  }

  get form() {
    const answer = getAnswer(this.raw.document, "form-type");
    return answer?.node.question.options.edges.find(
      (edge) => edge.node.slug === answer?.node.stringValue
    )?.node.label;
  }

  get instanceState() {
    return this.instance?.get("instanceState.uppercaseName");
  }

  get coordination() {
    const description = this.instance?.get("form.description");

    return description && description.split(";")[0];
  }
  get reason() {
    //TODO camac_legacy: Not yet implemented
    return null;
  }
  get caseStatus() {
    //TODO camac_legacy: Not yet implemented
    return null;
  }

  get buildingProjectStatus() {
    const answer = getAnswer(this.raw.document, "status-bauprojekt");
    return answer?.node.question.options.edges.find(
      (edge) => edge.node.slug === answer?.node.stringValue
    )?.node.label;
  }

  get parcelNumbers() {
    const answer = getAnswer(this.raw.document, "parcels");
    const tableAnswers = answer?.node.value ?? [];
    return tableAnswers.map(
      (answer) => getAnswer(answer, "parcel-number")?.node.stringValue
    );
  }

  get egridNumbers() {
    const answer = getAnswer(this.raw.document, "parcels");
    const tableAnswers = answer?.node.value ?? [];
    return tableAnswers
      .map((answer) => getAnswer(answer, "e-grid")?.node.stringValue)
      .filter(Boolean);
  }

  get activationWarning() {
    const activations = this.store.peekAll("activation");
    const activation = activations
      .filter(
        (activation) =>
          Number(activation.get("circulation.instance.id")) === this.instanceId
      )
      .filter(
        (activation) => activation.state === "NFD" || activation.state === "RUN"
      )[0];

    if (!activation) {
      return null;
    }

    const now = moment();
    if (activation.state === "NFD") {
      return "nfd";
    } else if (moment(activation.deadlineDate) < now) {
      return "expired";
    } else if (moment(activation.deadlineDate).subtract("2", "weeks") < now) {
      return "due-shortly";
    }

    return null;
  }

  static fragment = `{
    meta
    id
    document {
      answers(questions: [
        "applicant",
        "landowner",
        "project-author",
        "parcel-street",
        "street-number",
        "form-type",
        "proposal-description",
        "municipality",
        "parcels",
        "status-bauprojekt",
        "leitbehoerde",
      ]) {
        edges {
          node {
            question {
              slug
              ... on ChoiceQuestion{
                options {
                  edges {
                    node {
                      slug
                      label
                    }
                  }
                }
              }
            }

            ... on TableAnswer {
              value {
                answers {
                  edges {
                    node {
                      question {
                        slug
                      }
                      ... on StringAnswer {
                        stringValue: value
                      }
                    }
                  }
                }
              }
            }
            ... on StringAnswer {
              stringValue: value
            }
            ... on IntegerAnswer {
              integerValue: value
            }
          }
        }
      }
    }
  }`;
}
