import { GroupEditModel } from "./model";
import { GroupEditorApi } from "./api";
import { renderHeader } from "./render/header";

export class GroupEditor extends HTMLElement {
  private model!: GroupEditModel;
  private mode!: "create" | "edit";
  private groupId: string | null = null;

  public api!: GroupEditorApi;

  public config = {
    redirectOnSuccess: undefined as undefined | ((id: string) => string),
    presentation: "page" as "page" | "modal",
  };

  connectedCallback() {
    if (!this.api) {
      throw new Error("<group-editor> requires a api to be injected")
    }
    this.mode = this.getAttribute("mode") as "create" | "edit"
    this.groupId = this.getAttribute("group-id")

    this.model = GroupEditModel.initial(this.mode)

    this.renderSkeleton();

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