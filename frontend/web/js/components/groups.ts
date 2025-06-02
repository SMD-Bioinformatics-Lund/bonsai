import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("groups-component")
export class GroupsComponent extends LitElement {
  render() {
    return html`
      <div class="container">
        <h1>Groups</h1>
        <p> This is a placeholder for the groups component.</p>
      </div>`;
  }
}