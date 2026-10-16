import { GroupEditModel } from "../model";

export function renderActions(
  container: HTMLElement,
  model: GroupEditModel,
  handlers: { onSave: () => void; onReset: () => void; onDelete: () => void }
) {
  const deleteButton = model.mode === "edit"
    ? `<button id="ge-delete" class="btn btn-outline-danger me-auto">Delete group</button>`
    : "";

  container.innerHTML = `
    ${deleteButton}
    <button id="ge-reset" class="btn btn-outline-secondary">Reset</button>
    <button id="ge-save" class="btn btn-success">
      ${model.mode === "create" ? "Create group" : "Save changes"}
    </button>
  `;

  container.querySelector("#ge-reset")!.addEventListener("click", handlers.onReset);
  container.querySelector("#ge-save")!.addEventListener("click", handlers.onSave);
  container.querySelector("#ge-delete")?.addEventListener("click", handlers.onDelete);
}
