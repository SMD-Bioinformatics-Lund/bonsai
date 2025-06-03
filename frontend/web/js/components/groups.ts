import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { onEvent } from "../event-bus";
import { GroupInfo } from "../types";

@customElement("group-component")
export class GroupComponent extends LitElement {
  @property({ type: Object })
  accessor groupInfo: GroupInfo;

  protected render() {
    return html`
      <div class="card group-card position-relative">
        <a
          class="d-inline-block badge bage-pill bg-secondary edit-button position-absolute top-0 start-100 translate-middle"
          role="button"
          href="/"
        >
          <i class="bi bi-pencil"></i>
        </a>
      </div>
    `;
  }
}

/* Render cards for each group. */
@customElement("groups-component")
export class GroupsComponent extends LitElement {
  @state()
  private accessor groupInfo: any[] = [];

  connectedCallback(): void {
    super.connectedCallback();
    onEvent("samples:deleted", () => {
      this.groupInfo = []; //await this.getGroupsInfo();
    });
  }

  render() {
    return html` <div class="container">
      <h1>Groups</h1>
      <p>This is a placeholder for the groups component.</p>
    </div>`;
  }
}
