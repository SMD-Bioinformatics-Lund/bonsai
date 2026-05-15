import { GroupEditModel, EditorMode } from "./model";
import { renderLayout } from "./render/layout";

export function initGroupEditor(): void {
  const mount = document.getElementById("group-editor");

  if (!mount) {
    console.error("Group editor mount element not found");
    return;
  }

  const mode = mount.dataset.mode as EditorMode;
  const groupId = mount.dataset.groupId ?? null;

  const model: GroupEditModel = {
    mode,
    groupId,
    displayName: "",
    description: ""
  };

  renderLayout(mount, model);
}
