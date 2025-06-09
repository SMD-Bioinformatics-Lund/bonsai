import { onEvent } from "../event-bus";
import { GroupInfo } from "../types";
import { LitElement, html, TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";

function editGroupButton(groupId: string): TemplateResult {
  return html`
    <a
      class="d-inline-block badge bage-pill bg-secondary edit-button position-absolute top-0 start-100 translate-middle"
      role="button"
      href="/groups/edit/${groupId}"
    >
      <i class="bi bi-pencil"></i>
    </a>
  `;
}

function groupCardTemplate(group: GroupInfo, isAdmin: boolean): TemplateResult {
  return html`
    <div class="col-sm-6 col-md-4 col-lg-auto py-2">
      <div class="card group-card position-relative">
        ${isAdmin ? editGroupButton(group.group_id) : ""}
        <a
          href="/groups/${group.group_id}"
          class="text-decoration-none text-dark"
        >
          <div class="card-body">
            <h5 class="card-title">${group.display_name}</h5>
            <span class="text-muted text-uppercase fw-semibold n-samples"
              >Samples: ${group.included_samples.length}</span
            >
            ${group.description
              ? html`<p class="card-text text-wrap"
                  >${group.description}</p>`
              : ""}
          </div>
          <div
            class="card-footer text-body-secondary text-muted py-1 text-uppercase fw-semibold"
          >
            <span class="last-update text-uppercase fw-semibold text-muted">
              Updated: ${new Date(group.modified_at).toLocaleDateString()}
            </span>
          </div>
        </a>
      </div>
    </div>
  `;
}

@customElement("group-list")
export class GroupList extends LitElement {
  @property({ attribute: false }) accessor getGroupInfo!: () => Promise<
    GroupInfo[]
  >;
  @property({ type: Boolean }) accessor isAdmin = false;

  @state() private accessor groups: GroupInfo[] = [];

  connectedCallback() {
    super.connectedCallback();
    this.loadGroups();
    this.setupEventListeners();
  }

  setupEventListeners() {
    onEvent("samples:deleted", () => this.loadGroups())
    onEvent("samples:added-to-group", () => this.loadGroups())
  };

  async loadGroups() {
    if (this.getGroupInfo) {
      try {
        this.groups = await this.getGroupInfo();
      } catch (err) {
        console.error("Failed to load groups:", err);
      }
    }
  }

  protected createRenderRoot(): HTMLElement | DocumentFragment {
    // Override the default shadow DOM to use light DOM
    // This allows the component to be styled with bootstrap classes
    return this;
  }

  render() {
    return html`
      <div class="row">
        ${this.groups.map((group) => groupCardTemplate(group, this.isAdmin))}
        ${this.isAdmin
          ? html`
          <div class="col-sm-6 col-md-4 col-lg-auto py-2">
            <a class="card group-card position-relative text-center border-secondary h-100 d-flex align-items-center justify-content-center" href="/groups/edit">
              <div class="rounded-circle bg-secondary text-white fw-bold d-flex align-items-center justify-content-center" style="width: 3.75rem; height: 3.75rem; font-size: 2.5rem; line-height: 0;">
                <i class="bi bi-plus-lg"></i>
              </div>
              </a>
            </div>`
          : ""}
      </div>
    `;
  }
}
