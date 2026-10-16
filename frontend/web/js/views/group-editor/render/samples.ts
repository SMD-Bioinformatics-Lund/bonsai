import { GroupEditModel } from "../model";

export function renderSamples(
  container: HTMLElement,
  model: GroupEditModel
) {
  container.innerHTML = `
    <h6 class="mb-2">Samples in group</h6>

    <ul class="list-group list-group-flush">
      ${model.samples.length === 0
        ? `<li class="list-group-item text-muted small">
             No samples added yet.
           </li>`
        : model.samples.map(s => `
            <li class="list-group-item">${s}</li>
          `).join("")}
    </ul>
  `;
}