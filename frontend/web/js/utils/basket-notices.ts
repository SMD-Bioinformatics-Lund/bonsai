import type { ApiAlleleSchemeValidation } from "../core/types";

export type BasketNotice = Pick<ApiAlleleSchemeValidation, "details" | "groups"> & {
  method?: string;
  notice: string;
};

function createNoticeCategory(
  detail: string,
  sampleIds: string[],
  onRemove: (sampleIds: string[]) => void,
): HTMLLIElement {
  const item = document.createElement("li");
  item.className = "mb-2";
  const newline = detail.indexOf("\n");
  const label = document.createElement("strong");
  label.textContent = (newline > 0 ? detail.slice(0, newline) : detail).replace(/:$/, "");
  if (newline > 0) {
    item.appendChild(label);
    const samples = document.createElement("div");
    samples.style.whiteSpace = "pre-line";
    samples.textContent = detail.slice(newline + 1);
    item.appendChild(samples);
  } else {
    item.textContent = detail;
  }
  if (sampleIds.length > 0) {
    if (newline <= 0) {
      item.textContent = "";
      item.appendChild(label);
    }
    label.className = "d-flex justify-content-between align-items-start gap-2";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-link btn-sm text-danger p-0 flex-shrink-0";
    remove.title = `Remove ${sampleIds.length} ${sampleIds.length === 1 ? "sample" : "samples"} from basket`;
    remove.setAttribute("aria-label", `Remove ${detail.split("\n")[0].replace(/:$/, "")} from basket`);
    const trash = document.createElement("i");
    trash.className = "bi bi-trash";
    trash.setAttribute("aria-hidden", "true");
    remove.appendChild(trash);
    remove.addEventListener("click", () => onRemove(sampleIds));
    label.appendChild(remove);
  }
  return item;
}

export function createBasketNotices(
  notices: BasketNotice[],
  onRemove: (sampleIds: string[]) => void,
): HTMLDetailsElement {
  const disclosure = document.createElement("details");
  disclosure.className = "basket-notices small mt-3 mb-2";
  disclosure.setAttribute("data-test-id", "basket-notices");
  const summary = document.createElement("summary");
  summary.className = "text-secondary";
  const icon = document.createElement("i");
  icon.className = "bi bi-info-circle me-1";
  icon.setAttribute("aria-hidden", "true");
  summary.appendChild(icon);
  const count = document.createElement("span");
  count.textContent = `${notices.length} ${notices.length === 1 ? "notice" : "notices"}`;
  summary.appendChild(count);
  disclosure.appendChild(summary);
  for (const { method, notice, details, groups } of notices) {
    const section = document.createElement("section");
    section.className = "mt-3";
    if (method) {
      const heading = document.createElement("h6");
      heading.className = "fw-bold mb-1";
      heading.textContent = method;
      section.appendChild(heading);
    }
    const explanation = document.createElement("p");
    explanation.className = "mb-2";
    const prefix = `Cannot cluster by ${method}: `;
    const reason = notice.startsWith(prefix) ? notice.slice(prefix.length) : notice;
    explanation.textContent = reason.charAt(0).toUpperCase() + reason.slice(1);
    section.appendChild(explanation);
    const categories = groups?.length ? groups : (details || []).map(detail => ({ detail, sample_ids: [] }));
    if (categories.length) {
      const list = document.createElement("ul");
      list.className = "list-unstyled mb-0 ms-2 text-break";
      for (const { detail, sample_ids: sampleIds } of categories) {
        list.appendChild(createNoticeCategory(detail, sampleIds, onRemove));
      }
      section.appendChild(list);
    }
    disclosure.appendChild(section);
  }
  return disclosure;
}
