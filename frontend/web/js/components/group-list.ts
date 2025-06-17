import { onEvent } from "../utils/event-bus";
import { GroupInfo } from "../types";

// Helper to create group card HTML
function groupCardHTML(group: GroupInfo, isAdmin: boolean): string {
  return String.raw`
    <div class="col-sm-6 col-md-4 col-lg-auto py-2">
      <div class="card group-card position-relative">
        ${isAdmin ? `<a class="d-inline-block badge bage-pill bg-secondary edit-button position-absolute top-0 start-100 translate-middle" role="button" href="/groups/edit/${group.group_id}"><i class="bi bi-pencil"></i></a>` : ""}
        <a href="/groups/${group.group_id}" class="text-decoration-none text-dark">
          <div class="card-body">
            <h5 class="card-title">${group.display_name}</h5>
            <span class="text-muted text-uppercase fw-semibold n-samples">Samples: ${group.included_samples.length}</span>
            ${group.description ? `<p class="card-text text-wrap">${group.description}</p>` : ""}
          </div>
          <div class="card-footer text-body-secondary text-muted py-1 text-uppercase fw-semibold">
            <span class="last-update text-uppercase fw-semibold text-muted">
              Updated: ${new Date(group.modified_at).toLocaleDateString()}
            </span>
          </div>
        </a>
      </div>
    </div>
  `;
}

export class GroupList extends HTMLElement {
  getGroupInfo: (() => Promise<GroupInfo[]>) | null = null;
  isAdmin: boolean = false;
  groups: GroupInfo[] = [];

  constructor() {
    super();
  }

  connectedCallback() {
    this.loadGroups();
    this.setupEventListeners();
  }

  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (name === "is-admin") {
      this.isAdmin = this.hasAttribute("is-admin");
      this.render();
    }
  }

  setupEventListeners() {
    onEvent("samples:deleted", () => this.loadGroups());
    onEvent("samples:added-to-group", () => this.loadGroups());
  }

  async loadGroups() {
    if (this.getGroupInfo) {
      try {
        this.groups = await this.getGroupInfo();
        this.render();
      } catch (err) {
        console.error("Failed to load groups:", err);
      }
    }
  }

  render() {
    let html = `<div class="row">`;
    for (const group of this.groups) {
      html += groupCardHTML(group, this.isAdmin);
    }
    if (this.isAdmin) {
      html += String.raw`
        <div class="col-sm-6 col-md-4 col-lg-auto py-2">
          <a class="card group-card position-relative text-center border-secondary h-100 d-flex align-items-center justify-content-center" href="/groups/edit">
            <div class="rounded-circle bg-secondary text-white fw-bold d-flex align-items-center justify-content-center" style="width: 3.75rem; height: 3.75rem; font-size: 2.5rem; line-height: 0;">
              <i class="bi bi-plus-lg"></i>
            </div>
          </a>
        </div>
      `;
    }
    html += `</div>`;
    this.innerHTML = html;
  }
}

customElements.define("group-list", GroupList);