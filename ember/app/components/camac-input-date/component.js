import Component from "@ember/component";

export default Component.extend({
  change(e) {
    e.preventDefault();

    this.getWithDefault("attrs.on-change", () => {})(e.target.value);
  }
});
