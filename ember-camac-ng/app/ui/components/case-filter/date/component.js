import { action } from "@ember/object";
import Component from "@glimmer/component";
import moment from "moment";

export default class CaseFilterDateComponent extends Component {
  get value() {
    return this.args.value ? new Date(this.args.value) : null;
  }

  get maxDate() {
    return this.args.maxDate ? new Date(this.args.maxDate) : null;
  }
  get minDate() {
    return this.args.minDate ? new Date(this.args.minDate) : null;
  }

  @action
  updateFilter(date) {
    this.args.updateFilter({
      target: { value: date && moment(date).format(moment.HTML5_FMT.DATE) },
    });
  }
}
