import { GroupEditModel } from "./model";
import { GroupEditorApi } from "./api";
import { renderMeta } from "./render/meta";
import { initGroupEditor } from "./init"
import { renderColumns } from "./render/columns";
import { renderSamples } from "./render/samples";
import { renderActions } from "./render/actions";

import { ManifestColumn } from "core/types";
import { ColumnSelector } from "components/column-selector";

export class GroupEditor extends HTMLElement {
  private model!: GroupEditModel;
  private mode!: "create" | "edit";
  private groupId: string | null = null;
  private availableColumns: ManifestColumn[] = [];

  private _api?: GroupEditorApi;
  private isInitialized = false;
  private saving = false;
  private savedCore = { display_name: "", description: "" };
  private savedColumns: string[] = [];

  set api(api: GroupEditorApi) {
    this._api = api;
    this.initialize()
  }

  get api(): GroupEditorApi {
    if (!this._api) {
      throw new Error("<group-editor> API not available")
    }
    return this._api
  }

  public config = {
    redirectOnSuccess: undefined as undefined | ((id: string) => string),
    redirectOnDelete: undefined as undefined | string,
    presentation: "page" as "page" | "modal",
  };

  connectedCallback() {
    this.groupId = this.getAttribute("group-id");
    this.mode = this.getAttribute("mode") as "create" | "edit";

    this.model = GroupEditModel.initial(this.mode);

    this.renderSkeleton();
    this.isInitialized = true;
    this.initialize()
    .catch(err => console.error("Failed to initialize <group-editor>", err));
  }

  private async initialize() {
    if (!this.isInitialized || !this._api) return;

    // Fetch data
    this.availableColumns = await this.api.getAvailableColumns().then(resp => resp.columns);
    
    // Safe to proceed
    if (this.mode == "edit" && this.groupId) {
      this.load(this.groupId)
    } else {
      this.render()
    }
  }

  async load(groupId: string) {
    const data = await this.api.getGroup(groupId)
    this.model.loadFromApi(data);
    this.savedCore = { display_name: data.display_name, description: data.description };
    this.savedColumns = [...data.table_columns];
    this.render();
  }

  async save() {
    if (this.saving) return;
    if (!this._api) {
      throw new Error("<group-editor> cannot save without API");
    }

    this.setSaving(true);
    let coreSaved = false;
    try {
      // post updates to group
      let groupId: string;

      // create or update core info
      const corePayload = {
        display_name: this.model.displayName,
        description: this.model.description,
      }
      const selector = this.querySelector('column-selector') as ColumnSelector;
      const columns = selector.items.filter(item => item.enabled).map(item => item.id);
      const creating = this.mode === "create";
      if ( this.mode == "create" ) {
        // The group key is stable and cannot be changed afterwards.
        const groupObj = await this._api.createGroup({ ...corePayload, group_key: this.model.groupKey })
        groupId = groupObj.group_id;
        this.model.groupId = groupId;
        this.mode = "edit";
        this.model.mode = "edit";
        this.savedCore = { ...corePayload };
        coreSaved = true;
      } else {
        groupId = this.model.groupId!;
        // Only changed fields belong to this draft; preserve independent edits in other tabs.
        const changes: Partial<typeof corePayload> = {};
        if (corePayload.display_name !== this.savedCore.display_name) changes.display_name = corePayload.display_name;
        if (corePayload.description !== this.savedCore.description) changes.description = corePayload.description;
        if (Object.keys(changes).length) {
          await this._api.updateGroup(groupId, changes);
          this.savedCore = { ...corePayload };
          coreSaved = true;
        }
      }

      // update allowed columns
      // first narrow to only selected elements then get the col id
      if (creating || JSON.stringify(columns) !== JSON.stringify(this.savedColumns)) {
        await this._api.updateAllowedColumns(groupId, columns);
        this.savedColumns = [...columns];
      }

      this.dispatchEvent(
        new CustomEvent("group-editor:saved", {
          detail: { groupId, mode: this.mode },
        }),
      );

      if (this.config.redirectOnSuccess) {
        const url = typeof this.config.redirectOnSuccess === "function"
        ? this.config.redirectOnSuccess(this.model.groupId)
        : this.config.redirectOnSuccess;

        /* only change url if it's different */
        if (window.location.pathname !== url) {
          window.location.href = url;
        }
      }
    } catch (err) {
      this.dispatchEvent(
        new CustomEvent("group-editor:error", {
          detail: { message: coreSaved
            ? "Group details were saved, but column settings could not be confirmed. Retry to finish saving."
            : "Failed to save group: some changes may have been saved. Check the group before retrying.", cause: err }
        })
      )
    } finally {
      this.setSaving(false);
    }
  }

  private setSaving(saving: boolean) {
    this.saving = saving;
    this.inert = saving;
    this.setAttribute("aria-busy", String(saving));
    this.querySelectorAll<HTMLButtonElement>(".ge-actions button").forEach(button => { button.disabled = saving; });
  }

  private async delete() {
    if (this.saving) return;
    const groupId = this.model.groupId;
    if (this.mode !== "edit" || !groupId) return;

    const samples = this.model.sampleCount
      ? ` Its ${this.model.sampleCount} sample(s) will stay in Bonsai but leave the group.`
      : "";
    if (!window.confirm(`Delete the group "${this.model.displayName}"?${samples}`)) return;

    try {
      await this.api.deleteGroup(groupId);
    } catch (err) {
      this.dispatchEvent(
        new CustomEvent("group-editor:error", {
          detail: { message: "Failed to delete group", cause: err },
        }),
      );
      return;
    }

    this.dispatchEvent(
      new CustomEvent("group-editor:deleted", { detail: { groupId } }),
    );

    if (this.config.redirectOnDelete) {
      window.location.href = this.config.redirectOnDelete;
    }
  }

  private reset() {
    if (this.saving) return;
    if (this.mode === "edit" && this.model.groupId) {
      this.load(this.model.groupId);
    } else {
      this.model.groupKey = "";
      this.model.displayName = "";
      this.model.description = "";
      this.model.samples = [];
    }
    this.render();
  }

  async renderSkeleton() {
    this.innerHTML = String.raw`
      <div class="card shadow-sm group-editor-card">
        <div class="card-body">

          <section class="ge-meta"></section>
          <hr />

          <section class="ge-columns">
            <column-selector></column-selector>
          </section>
          <hr />

          <section class="ge-samples"></section>
          <hr />

          <section class="ge-actions d-flex justify-content-end gap-2"></section>

        </div>
      </div>
    `
  }

  async render() {
    renderMeta(
      this.querySelector(".ge-meta")!,
      this.model
    );

    renderColumns(
      this.querySelector("column-selector")!,
      this.availableColumns,
      this.model
    );

    renderSamples(
      this.querySelector(".ge-samples")!,
      this.model
    );

    renderActions(
      this.querySelector(".ge-actions")!,
      this.model,
      {
        onSave: () => this.save(),
        onReset: () => this.reset(),
        onDelete: () => this.delete(),
      }
    );
  }
}

customElements.define("group-editor", GroupEditor);

initGroupEditor()
