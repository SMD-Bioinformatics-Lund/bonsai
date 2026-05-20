import { GroupEditModel } from "../model";

export function renderActions(
  container: HTMLElement,
  model: GroupEditModel,
  handlers: { onSave: () => void; onReset: () => void }
) {
  container.innerHTML = `
    <button class="btn btn-outline-secondary">Reset</button>
    <button class="btn btn-success">
      ${model.mode === "create" ? "Create group" : "Save changes"}
    </button>
  `;

  const [resetBtn, saveBtn] = Array.from(
    container.querySelectorAll("button")
  );

  resetBtn.addEventListener("click", handlers.onReset);
  saveBtn.addEventListener("click", handlers.onSave);
}
``