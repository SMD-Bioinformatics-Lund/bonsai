import { GroupEditModel } from "../model";

export function renderMeta(
  container: HTMLElement,
  model: GroupEditModel
) {
  container.innerHTML = String.raw`
    <h5 class="mb-2">Group details</h5>
    <div class="mb-3">
      <label class="form-label fw-semibold mb-1 text-start" for="group-name">
        Group name<span class="text-danger">*</span>
      </label>
      <input
        id="group-name"
        type="text"
        class="form-control"
        value="${model.displayName}"
      />
    </div>
    <div class="mb-3">
      <label for="group-description" class="form-label fw-semibold text-start">
        Description
      </label>
      <textarea
        id="group-description"
        class="form-control"
        rows="3"
      >${model.description}</textarea>
    </div>
  `;

  const nameInput = container.querySelector("input")!;
  const descInput = container.querySelector("textarea")!;

  nameInput.addEventListener("input", e => {
    model.displayName = (e.target as HTMLInputElement).value;
  });

  descInput.addEventListener("input", e => {
    model.description = (e.target as HTMLTextAreaElement).value;
  });
}
