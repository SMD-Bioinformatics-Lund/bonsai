import { GroupEditModel } from "../model";

export function renderHeader(
  container: HTMLElement,
  model: GroupEditModel
): void {
  container.replaceChildren(
    createTitle(model),
    createDescription(model),
    createMeta(model)
  );
}

function createTitle(model: GroupEditModel): HTMLElement {
  const wrapper = document.createElement("div");
  wrapper.className = "group-header-title";

  const h1 = document.createElement("h1");
  h1.textContent =
    model.mode === "create"
      ? "Create group"
      : model.displayName || "Edit group";

  wrapper.appendChild(h1);

  if (model.groupId) {
    const code = document.createElement("code");
    code.textContent = model.groupId;
    wrapper.appendChild(code);
  }

  return wrapper;
}

function createDescription(model: GroupEditModel): HTMLElement {
  const textarea = document.createElement("textarea");
  textarea.placeholder = "Group description";
  textarea.value = model.description;

  textarea.addEventListener("input", () => {
    model.description = textarea.value;
  });

  return textarea;
}

function createMeta(model: GroupEditModel): HTMLElement {
  const meta = document.createElement("div");
  meta.className = "group-header-meta";
  meta.textContent = model.sampleCount !== undefined ? `Samples: ${model.sampleCount}` : "No samples";

  return meta;
}