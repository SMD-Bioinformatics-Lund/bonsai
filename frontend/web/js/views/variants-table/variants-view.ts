import Choices from "choices.js";
import DataTable from "datatables.net-bs5";
import { initTooltip } from "utils/notification";

const selectedVariants = new Map<string, {
  variant_id: string;
  analysis_id: string;
  analysis_type: string;
}>();

export function initVariantsView(): void {
  initSelects();
  initButtons();
  initVariantSelection();
  initVariantTables();
  initTooltip();
  resetSelectedOnLoad();
}

function initSelects(): void {
  const selectors = [
    "#antibiotic-group",
    "#filter-genes",
    "#filter-who-class",
    "#filter-variant-type"
  ];

  selectors.forEach(selector => {
    const el = document.querySelector(selector) as HTMLSelectElement | null;

    if (!el) return;

    new Choices(el, {
      searchEnabled: true,
      itemSelectText: '',
      shouldSort: false
    });
  });
}

/* Initialize bootstrap tables */
function initVariantTables(): void {
  const tables = [
    '#tb-profiler-variant-tbl',
    '#sv-variant-tbl',
  ]

  tables.forEach(tbl => {
    const el = document.querySelector(tbl) as HTMLTableElement | null;

    if (!el) return;

    return new DataTable(tbl, {
      paging: false,
      select: false,
      searching: true,
    });
  })
}

function initButtons(): void {
  const acceptBtn = document.getElementById("accept-variant-btn");
  const rejectBtn = document.getElementById("reject-variant-btn");

  const rejection = document.getElementById("rejection-reason-group") as HTMLSelectElement;
  const antibiotic = document.getElementById("antibiotic-group") as HTMLSelectElement;
  const highRes = document.getElementById("high-res-btn") as HTMLButtonElement;
  const lowRes = document.getElementById("low-res-btn") as HTMLButtonElement;

  acceptBtn?.addEventListener("click", () => {
    rejection.disabled = true;
    antibiotic.disabled = false;
    highRes.disabled = false;
    lowRes.disabled = false;
  });

  rejectBtn?.addEventListener("click", () => {
    rejection.disabled = false;
    antibiotic.disabled = true;
    highRes.disabled = true;
    lowRes.disabled = true;
  });
}

function initVariantSelection(): void {
  // individual checkboxes
  document
    .querySelectorAll<HTMLInputElement>(".br-content input[type='checkbox'][data-variant-id]")
    .forEach(cb => {
      cb.addEventListener("change", () => selectVariant(cb));
    });

  // "select all"
  const selectAll = document.getElementById("select-all-variants") as HTMLInputElement;

  selectAll?.addEventListener("change", () => {
    selectAllVariants(selectAll, "tbprofiler-variant-table");
  });
}

function selectVariant(element: HTMLInputElement): void {
  const item = {
    variant_id: element.dataset.variantId!,
    analysis_id: element.dataset.analysisId!,
    analysis_type: element.dataset.analysisType!,
  };

  const key = JSON.stringify(item);

  if (element.checked) {
    selectedVariants.set(key, item);
  } else {
    selectedVariants.delete(key);
  }

  const payload = Array.from(selectedVariants.values());

  const input = document.getElementById("curations-input") as HTMLInputElement;
  if (input) {
    input.value = JSON.stringify(payload);
  }

  const counter = document.getElementById("selected-variants-counter");
  if (counter) {
    counter.textContent = String(selectedVariants.size);
  }
}

function selectAllVariants(elem: HTMLInputElement, tableId: string): void {
  const table = document.getElementById(tableId);
  if (!table) return;

  table
    .querySelectorAll<HTMLInputElement>("input[type='checkbox'][data-variant-id]")
    .forEach(el => {
      el.checked = elem.checked;
      selectVariant(el);
    });
}

function resetSelectedOnLoad(): void {
  selectedVariants.clear();
  document.querySelectorAll<HTMLInputElement>('.br-content input[type="checkbox"]')
    .forEach(input => { input.checked = false; });
  const input = document.getElementById("curations-input") as HTMLInputElement | null;
  if (input) input.value = "[]";
  const counter = document.getElementById("selected-variants-counter");
  if (counter) counter.textContent = "0";
}
