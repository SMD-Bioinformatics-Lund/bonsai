import { emitEvent } from "../utils/event-bus";
import { GroupInfo, MembershipEdges } from "../types";
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
  getGroupInfo: (() => Promise<ApiGroupInfoResponse>) | null = null;
  getSelectedSamples: (() => string[]) | null = null;
  getGroupMembership:
    | ((sampleIds: string[], signal?: AbortSignal) => Promise<MembershipEdges>)
    | null = null;
  addToGroup: ((groupId: string, sampleIds: string[]) => Promise<void>) | null = null;
  removeFromGroup: ((groupId: string, sampleIds: string[]) => Promise<void>) | null = null;

  private shadow!: ShadowRoot;
  private selector: ChoiceSelect;
  private applyBtn: HTMLButtonElement;
  private clearBtn: HTMLButtonElement;

  private membershipAbort?: AbortController;
  private currentSelectedSamples: string[] = [];
  private currentMemberships: MembershipBySample = {};

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadow = this.shadowRoot!;
    this.shadow.appendChild(template.content.cloneNode(true));
    this.selector = this.shadow.getElementById("groups") as ChoiceSelect;
    this.applyBtn = this.shadow.getElementById("apply") as HTMLButtonElement;
    this.clearBtn = this.shadow.getElementById("clear") as HTMLButtonElement;
  }

  connectedCallback(): void {
    this.applyBtn.addEventListener("click", this.onApply);
    this.clearBtn.addEventListener("click", this.onClear);
    // wait for choice-select to be fully initialized
    customElements.whenDefined("choice-select").then(() => {
      this.loadGroups();
      this.onSelectedSamplesChange();
    });
  }

  disconnectedCallback(): void {
    this.applyBtn.removeEventListener("click", this.onApply);
    this.clearBtn.removeEventListener("click", this.onClear);
  }

  /**
   * Call this when the selected samples change (e.g., row selection in table).
   * This will preselect groups that all selected samples are members of.
   */
  onSelectedSamplesChange = async () => {
    const sampleIds = this.getSelectedSamples?.() ?? [];
    this.currentSelectedSamples = sampleIds;
    await this.preselectGroupsForSamples(sampleIds);
  };
  private onApply = async () => {
    if (!this.getSelectedSamples || !this.addToGroup || !this.removeFromGroup) return;

    const sampleIds = this.getSelectedSamples();
    const selectedGroupIds: string[] = this.selector.getSelected();

    if (!sampleIds.length) {
      this.dispatchEvent(
        new CustomEvent("apply:skipped", { detail: { reason: "no_samples" }, bubbles: true }),
      );
      return;
    }

    try {
      // For each sample, compute which groups to add/remove
      // A sample should be in ALL selected groups and in NO deselected groups
      for (const sampleId of sampleIds) {
        const currentGroups = new Set(this.currentMemberships[sampleId] ?? []);
        const targetGroups = new Set(selectedGroupIds);

        // Groups to add: in target but not in current
        const toAdd = [...targetGroups].filter(gid => !currentGroups.has(gid));
        // Groups to remove: in current but not in target
        const toRemove = [...currentGroups].filter(gid => !targetGroups.has(gid));

        if (toAdd.length > 0) {
          for (const gid of toAdd) {
            await this.addToGroup!(gid, [sampleId]);
          }
        }

        if (toRemove.length > 0) {
          for (const gid of toRemove) {
            await this.removeFromGroup!(gid, [sampleId]);
          }
        }
      }
      this.dispatchEvent(
        new CustomEvent("apply:success", { detail: { groupIds: selectedGroupIds, sampleIds }, bubbles: true }),
      );
    } catch (err) {
      console.error("Updating sample group memberships failed", err);
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
      const options = groups.data.map((g) => ({ value: g.group_id, label: g.display_name }));
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
      this.currentMemberships = {};
      return;
    }

    try {
      const membershipsEdges = await this.getGroupMembership(sampleIds, this.membershipAbort.signal);
      const memberships = groupMemberships(membershipsEdges);
      this.currentMemberships = memberships;
      
      const counts = new Map<string, number>();
      const nSamples = sampleIds.length;

      for (const sid of sampleIds) {
        // Dedupe groups within a sample to avoid overcounting
        const groupsForSample = new Set(memberships[sid] ?? []);
        for (const gid of groupsForSample) {
          counts.set(gid, (counts.get(gid) ?? 0) + 1);
        }
      }

      // Select only groups that ALL selected samples are members of (intersection)
      const groupNameIntersect = [...counts.entries()]
        .filter(([_, cnt]) => cnt === nSamples)
        .map(([gid]) => gid);

      groupNameIntersect.sort();
      this.selector.setSelected(groupNameIntersect);
    } catch (err) {
      console.warn("Failed to preselect samples", err);
    }
  }
}


type MembershipBySample = Record<string, string[]>;


function groupMemberships(
  edges: MembershipEdges,
  { dedupe = true, sort = true } = {}
): MembershipBySample {
  const map = new Map<string, Set<string>>();

  for (const { sample_id, group_id } of edges) {
    const set = map.get(sample_id) ?? new Set<string>();
    set.add(group_id);
    map.set(sample_id, set);
  }

  const result: MembershipBySample = {};
  for (const [sample_id, set] of map.entries()) {
    const arr = Array.from(set);
    result[sample_id] = sort ? arr.sort() : arr;
  }
  return result;
}


customElements.define("group-selector", GroupSelector);
