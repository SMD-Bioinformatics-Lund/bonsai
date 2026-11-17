import type { ApiAlleleSchemeValidation } from "../core/types";

export type BasketNotice = Pick<ApiAlleleSchemeValidation, "details" | "notice_groups"> & {
  method?: string;
  notice: string;
};

type NoticeActions = {
  onRemove: (sampleIds: string[]) => void;
  onSelect: (sampleIds: string[]) => void;
};

function createNoticeCategory(
  detail: string,
  sampleIds: string[],
  { onRemove, onSelect }: NoticeActions,
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
    const heading = document.createElement("span");
    heading.textContent = label.textContent;
    heading.style.minWidth = "0";
    label.textContent = "";
    label.appendChild(heading);
    label.className = "d-flex justify-content-between align-items-start gap-2";
    const actions = document.createElement("span");
    actions.className = "d-inline-flex align-items-center gap-2 flex-shrink-0";
    const select = document.createElement("button");
    select.type = "button";
    select.className = "btn btn-link btn-sm text-success px-1 py-0 flex-shrink-0";
    select.title = "Select this group: keep only these samples in the basket";
    select.setAttribute("aria-label", `Select only ${detail.split("\n")[0].replace(/:$/, "")} in basket`);
    const check = document.createElement("i");
    check.className = "bi bi-check2-square";
    check.setAttribute("aria-hidden", "true");
    select.appendChild(check);
    select.addEventListener("click", () => onSelect(sampleIds));
    actions.appendChild(select);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn btn-link btn-sm text-danger px-1 py-0 flex-shrink-0";
    remove.title = `Remove ${sampleIds.length} ${sampleIds.length === 1 ? "sample" : "samples"} from basket`;
    remove.setAttribute("aria-label", `Remove ${detail.split("\n")[0].replace(/:$/, "")} from basket`);
    const trash = document.createElement("i");
    trash.className = "bi bi-trash";
    trash.setAttribute("aria-hidden", "true");
    remove.appendChild(trash);
    remove.addEventListener("click", () => onRemove(sampleIds));
    actions.appendChild(remove);
    label.appendChild(actions);
  }
  return item;
}

export function createBasketNotices(
  notices: BasketNotice[],
  actions: NoticeActions,
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
  for (const { method, notice, details, notice_groups: noticeGroups } of notices) {
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
    const categories = noticeGroups?.length ? noticeGroups : (details || []).map(detail => ({ detail, sample_ids: [] }));
    if (categories.length) {
      const list = document.createElement("ul");
      list.className = "list-unstyled mb-0 ms-2 text-break";
      for (const { detail, sample_ids: sampleIds } of categories) {
        list.appendChild(createNoticeCategory(detail, sampleIds, actions));
      }
      section.appendChild(list);
    }
    disclosure.appendChild(section);
  }
  return disclosure;
}
