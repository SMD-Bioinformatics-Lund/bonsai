import Choices from "choices.js";
import DataTable from "datatables.net-bs5";
import { initTooltip } from "utils/notification";


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
    .querySelectorAll<HTMLInputElement>(".br-content input[type='checkbox']")
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
  const selected = new Set<string>(
    JSON.parse(localStorage.getItem("selectedVariants") || "[]")
  );

  const item = {
    variant_id: element.dataset.variantId!,
    analysis_id: element.dataset.analysisId!,
    analysis_type: element.dataset.analysisType!,
  };

  const key = `${item.analysis_id}:${item.analysis_type}:${item.variant_id}`;

  element.checked ? selected.add(key) : selected.delete(key);

  const payload = Array.from(selected).map(key => {
    const [analysis_id, analysis_type, variant_id] = key.split(":");
    return { analysis_id, analysis_type, variant_id };
  });

  const input = document.getElementById("curations-input") as HTMLInputElement;
  if (input) {
    input.value = JSON.stringify(payload);
  }

  localStorage.setItem("selectedVariants", JSON.stringify(Array.from(selected)));

  const counter = document.getElementById("selected-variants-counter");
  if (counter) {
    counter.textContent = String(selected.size);
  }
}

function selectAllVariants(elem: HTMLInputElement, tableId: string): void {
  const table = document.getElementById(tableId);
  if (!table) return;

  table
    .querySelectorAll<HTMLInputElement>("input[type='checkbox']")
    .forEach(el => {
      el.checked = elem.checked;
      selectVariant(el);
    });
}

function resetSelectedOnLoad(): void {
  const checked = Array.from(
    document.querySelectorAll<HTMLInputElement>('.br-content input[type="checkbox"]')
  )
    .filter(input => input.checked)
    .map(input => input.id);

  localStorage.setItem("selectedVariants", JSON.stringify(checked));
}
