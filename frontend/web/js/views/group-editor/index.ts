import { GroupEditModel } from "./model";
import { GroupEditorApi } from "./api";
import { renderMeta } from "./render/meta";
import { initGroupEditor } from "./init"
import { renderColumns } from "./render/columns";
import { renderSamples } from "./render/samples";
import { renderActions } from "./render/actions";

export class GroupEditor extends HTMLElement {
  private model!: GroupEditModel;
  private mode!: "create" | "edit";
  private groupId: string | null = null;

  private _api?: GroupEditorApi;
  private isInitialized = false;

  set api(api: GroupEditorApi) {
    this._api = api;
    this.tryInitialize()
  }

  get api(): GroupEditorApi {
    if (!this._api) {
      throw new Error("<group-editor> API not available")
    }
    return this._api
  }

  public config = {
    redirectOnSuccess: undefined as undefined | ((id: string) => string),
    presentation: "page" as "page" | "modal",
  };

  connectedCallback() {
    this.groupId = this.getAttribute("group-id");
    this.mode = this.getAttribute("mode") as "create" | "edit";

    this.model = GroupEditModel.initial(this.mode);

    this.renderSkeleton();
    this.isInitialized = true;
    this.tryInitialize();
  }

  private tryInitialize() {
    if (!this.isInitialized || !this._api) return;

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
    this.render();
  }

  async save() {
    if (!this._api) {
      throw new Error("<group-editor> cannot save without API");
    }

    try {
      // post updates to group
      const groupId = "temp-id"
      this.dispatchEvent(
        new CustomEvent("group-editor:saved", {
          detail: { groupId, mode: this.mode },
        }),
      );

      if (this.config.redirectOnSuccess) {
        const url = typeof this.config.redirectOnSuccess === "function"
        ? this.config.redirectOnSuccess(groupId)
        : this.config.redirectOnSuccess;
        window.location.href = url;
      }
    } catch (err) {
      this.dispatchEvent(
        new CustomEvent("group-editor:error", {
          detail: { message: "Failed to save group", cause: err }
        })
      )
    };
  }

  private reset() {
    this.model.displayName = "";
    this.model.description = "";
    this.model.allowedColumns = [];
    this.model.samples = [];
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
      }
    );
  }
}

customElements.define("group-editor", GroupEditor);

initGroupEditor()