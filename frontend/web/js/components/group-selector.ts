import { emitEvent } from "../utils/event-bus";
import { throwSmallToast } from "../utils/notification";
import { GroupInfo } from "../types";

export class GroupSelector extends HTMLElement {
  getGroupInfo: (() => Promise<GroupInfo[]>) | null = null;
  getSelectedSamples: (() => string[]) | null = null;
  AddToGroupFunc: ((groupId: string, sampleIds: string[]) => Promise<void>) | null = null;
  groups: GroupInfo[] = [];

  constructor() {
    super();
  }

  connectedCallback() {
    this.loadGroups();
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

  addSamplesToGroup = (e: Event) => {
    const target = e.target as HTMLElement;
    const groupId = target.getAttribute("data-group-id");
    if (!groupId || !this.getSelectedSamples || !this.AddToGroupFunc) return;
    const selectedSamples = this.getSelectedSamples();
    if (selectedSamples.length === 0) {
      throwSmallToast("No samples selected", "warning");
      return;
    }
    this.AddToGroupFunc(groupId, selectedSamples)
      .then(() => {
        emitEvent("samples:added-to-group", {});
        throwSmallToast(`Added ${selectedSamples.length} samples to group`, "success");
      })
      .catch((error) => {
        console.error(`Error adding ${selectedSamples.length} samples to group:`, error);
        throwSmallToast(`Error adding ${selectedSamples.length} samples to group`, "error");
      });
  };

  render() {
    let html = String.raw`
      <div class="dropdown ps-2 add-to-group-btn">
        <button class="btn btn-sm btn-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
          Add to group <i class="bi bi-folder-plus"></i>
        </button>
        <ul class="dropdown-menu">`;
    for (const group of this.groups) {
      html += `<li><a class="dropdown-item" data-group-id="${group.group_id}">${group.display_name}</a></li>`;
    }
    html += `</ul></div>`;
    this.innerHTML = html;
    // Attach click listeners
    this.querySelectorAll(".dropdown-item").forEach((el) => {
      el.addEventListener("click", this.addSamplesToGroup);
    });
  }
}

customElements.define("group-selector", GroupSelector);