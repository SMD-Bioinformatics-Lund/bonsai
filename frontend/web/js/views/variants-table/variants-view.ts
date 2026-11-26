import Choices from "choices.js";
import DataTable from "datatables.net-bs5";
import { initTooltip } from "utils/notification";

const selectedVariants = new Map<string, {
  variant_id: string;
  analysis_id: string;
  analysis_type: string;
  predictedResistance: Set<string>;
}>();

const choiceOptions = { searchEnabled: true, itemSelectText: "", shouldSort: false };

export function initVariantsView(): void {
  initSelects();
  const prefillResistance = initCurationForm();
  initVariantSelection(() => {
    renderVariantSelection();
    prefillResistance?.();
  });
  initVariantTables();
  initTooltip();
  resetSelectedOnLoad();
}

function initSelects(): void {
  for (const selector of ["#filter-genes", "#filter-who-class", "#filter-variant-type"]) {
    const select = document.querySelector<HTMLSelectElement>(selector);
    if (select) new Choices(select, choiceOptions);
  }
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
      // Keep the supplied variant order until a user sorts a data column.
      order: [],
    });
  })
}

function initCurationForm(): (() => void) | undefined {
  const antibiotic = document.querySelector<HTMLSelectElement>("#antibiotic-group");
  const form = antibiotic?.form;
  if (!form) return;

  const accept = form.querySelector<HTMLInputElement>("#accept-variant-btn");
  const reject = form.querySelector<HTMLInputElement>("#reject-variant-btn");
  const rejection = form.querySelector<HTMLSelectElement>("#rejection-reason-group");
  const confirm = form.querySelector<HTMLInputElement>("[name='classify-variant']");
  const levels = form.querySelectorAll<HTMLInputElement>("[name='resistance-lvl-btn']");
  const antibioticValues = new Map(
    Array.from(antibiotic.options, ({ value }) => [value.trim().toLowerCase(), value]),
  );
  const choices = new Choices(antibiotic, { ...choiceOptions, removeItemButton: true });

  function updateConfirm(): void {
    const hasDecisionDetails =
      (accept.checked && antibiotic.selectedOptions.length > 0) ||
      (reject.checked && Boolean(rejection.value));
    confirm.disabled = selectedVariants.size === 0 || !hasDecisionDetails;
  }

  function updateDecision(): void {
    rejection.disabled = !reject.checked;
    levels.forEach(level => { level.disabled = reject.checked; });
    if (reject.checked) choices.disable();
    else choices.enable();
  }

  accept.addEventListener("change", updateDecision);
  reject.addEventListener("change", updateDecision);
  form.addEventListener("change", updateConfirm);
  updateDecision();
  updateConfirm();

  return () => {
    const [first, ...others] = Array.from(selectedVariants.values(), variant => variant.predictedResistance);
    const shared = [...(first ?? [])].filter(value => others.every(predictions => predictions.has(value)));
    const uncatalogued = shared.filter(value => !antibioticValues.has(value));
    if (uncatalogued.length) {
      choices.setChoices(uncatalogued.map(value => ({
        value,
        label: value.charAt(0).toUpperCase() + value.slice(1),
      })));
      uncatalogued.forEach(value => antibioticValues.set(value, value));
    }
    choices.removeActiveItems();
    choices.setChoiceByValue(shared.map(value => antibioticValues.get(value)));
    updateConfirm();
  };
}

function initVariantSelection(updateSelection: () => void): void {
  // individual checkboxes
  document
    .querySelectorAll<HTMLInputElement>(".br-content input[type='checkbox'][data-variant-id]")
    .forEach(cb => {
      cb.addEventListener("change", () => {
        selectVariant(cb);
        updateSelection();
      });
    });

  document
    .querySelectorAll<HTMLTableSectionElement>("#tbprofiler-variant-table, #sv-variant-table")
    .forEach(body => {
      body.addEventListener("click", event => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest("a, button, input, select, textarea, label, form, [role='button'], [data-bs-toggle], [contenteditable='true']")) return;
        const checkbox = target.closest("tr")?.querySelector<HTMLInputElement>("input[type='checkbox']");
        if (checkbox && !checkbox.disabled) checkbox.click();
      });
    });

  // "select all"
  const selectAll = document.getElementById("select-all-variants") as HTMLInputElement;

  selectAll?.addEventListener("change", () => {
    selectAllVariants(selectAll, "tbprofiler-variant-table");
    updateSelection();
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
    const predictions: string[] = JSON.parse(element.dataset.predictedResistance ?? "[]");
    selectedVariants.set(key, {
      ...item,
      predictedResistance: new Set(
        predictions.map(name => name.trim().toLowerCase()).filter(Boolean),
      ),
    });
  } else {
    selectedVariants.delete(key);
  }
}

function renderVariantSelection(): void {
  const payload = Array.from(selectedVariants.values(), ({ variant_id, analysis_id, analysis_type }) => ({
    variant_id, analysis_id, analysis_type,
  }));

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
  renderVariantSelection();
}
