import { GroupEditModel } from "../model";
import { renderHeader } from "./meta";

export function renderLayout(
  mount: HTMLElement,
  model: GroupEditModel
): void {
  mount.replaceChildren();

  const headerSection = document.createElement("section");
  headerSection.className = "group-editor-header";

  const mainSection = document.createElement("section");
  mainSection.className = "group-editor-main";

  const actionBar = document.createElement("section");
  actionBar.className = "group-editor-action-bar";

  mount.append(headerSection, mainSection, actionBar);

  renderHeader(headerSection, model);

  // mainSection and actionBar will be populated later
}