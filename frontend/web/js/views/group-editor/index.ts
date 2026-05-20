import { GroupEditModel } from "./model";
import { GroupEditorApi } from "./api";
import { renderHeader } from "./render/header";
import { initGroupEditor } from "./init"

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

  async renderSkeleton() {
    this.innerHTML = String.raw`
      <section class="ge-header"></section>
      <section class="ge-body"></section>
      <section class="ge-action-bar"></section>
    `
  }

  async render() {
    renderHeader(
      this.querySelector(".ge-header"),
      this.model,
    );

    // render columns...
  }
}

customElements.define("group-editor", GroupEditor);

initGroupEditor()