import { emitEvent } from "../utils/event-bus";
import { GroupInfo, SampleGroupMembership } from "../types";
import { ChoiceSelect } from "../utils/choice-select";

const template = document.createElement("template");
template.innerHTML = String.raw`
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap/dist/css/bootstrap.min.css">
  <style>
    :host { display: inline-block; }
    .actions { display: flex; gap: .5rem; margin-top: .5rem; }
  </style>
      <div class="mb-3"><choice-select id="groups" multiple placeholder="Groups"></choice-select></div>
      <div class="mb-3 actions">
        <button id="apply" class="btn btn-sm btn-success">Apply</button>
        <button id="clear" class="btn btn-sm btn-outline-secondary">Clear</button>
      </div>
    </div>
  </div>
`;

export class GroupSelector extends HTMLElement {
  // dependancy injections set from outside function
  getGroupInfo: (() => Promise<GroupInfo[]>) | null = null;
  getSelectedSamples: (() => string[]) | null = null;
  getGroupMembership:
    | ((sampleIds: string[], signal?: AbortSignal) => Promise<SampleGroupMembership[]>)
    | null = null;
  addToGroup: ((groupId: string, sampleIds: string[]) => Promise<void>) | null = null;

  private shadow!: ShadowRoot;
  private selector: ChoiceSelect;
  private applyBtn: HTMLButtonElement;
  private clearBtn: HTMLButtonElement;

  private membershipAbort?: AbortController;

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadow = this.shadowRoot!;
    this.shadow.appendChild(template.content.cloneNode(true));
    this.selector = this.shadow.getElementById("groups");
    this.applyBtn = this.shadow.getElementById("apply") as HTMLButtonElement;
    this.clearBtn = this.shadow.getElementById("clear") as HTMLButtonElement;
  }

  connectedCallback(): void {
    this.applyBtn.addEventListener("click", this.onApply);
    this.clearBtn.addEventListener("click", this.onClear);
    // wait for choice-select to be fully initialized
    customElements.whenDefined("choice-select").then(() => {
      this.loadGroups();
    });
  }

  disconnectedCallback(): void {
    this.applyBtn.removeEventListener("click", this.onApply);
    this.clearBtn.removeEventListener("click", this.onClear);
  }

  private onApply = async () => {
    if (!this.getSelectedSamples || !this.addToGroup) return;

    const sampleIds = this.getSelectedSamples();
    const groupIds: string[] = this.selector.getSelected();

    if (!sampleIds.length || !groupIds.length) {
      this.dispatchEvent(
        new CustomEvent("apply:skipped", { detail: { reason: "empty" }, bubbles: true }),
      );
    }

    try {
      for (const gid of groupIds) {
        await this.addToGroup(gid, sampleIds);
      }
      this.dispatchEvent(
        new CustomEvent("apply:success", { detail: { groupIds, sampleIds }, bubbles: true }),
      );
    } catch (err) {
      console.error("Adding samples to group failed", err);
      this.dispatchEvent(new CustomEvent("apply:error", { detail: { error: err }, bubbles: true }));
    }
  };

  private onClear = () => {
    this.selector.clearSelected();
  };

  async loadGroups() {
    if (!this.getGroupInfo) {
      console.warn("No function for querying group info provided!", this);
      return;
    }

    try {
      const groups = await this.getGroupInfo();
      const options = groups.map((g) => ({ value: g.group_id, label: g.display_name }));
      this.selector.setChoices(options);
    } catch (err) {
      console.error("Failed to load groups:", err);
    }
  }

  /* Preselect the groups based on the selected samples */
  private async preselectGroupsForSamples(sampleIds: string[]) {
    if (this.membershipAbort) this.membershipAbort.abort();
    this.membershipAbort = new AbortController();

    if (!sampleIds?.length || !this.getGroupMembership) {
      this.selector.clearSelected();
      return;
    }

    try {
      const memberships = await this.getGroupMembership(sampleIds, this.membershipAbort.signal);
      const counts = new Map<string, number>();
      for (const sid of sampleIds) {
        for (const gid of memberships[sid] ?? []) {
          counts.set(gid, (counts.get(gid) ?? 0) + 1);
        }
      }
      // calculate the number of groups in total and
      const nSamples = sampleIds.length;
      const groupNameIntersect = [...counts.entries()]
        .filter(([_, cnt]) => cnt === nSamples)
        .map(([gid]) => gid);
      this.selector.setSelected(groupNameIntersect);
    } catch (err) {
      console.warn("Failed to preselect samples", err);
    }
  }
}

customElements.define("group-selector", GroupSelector);
