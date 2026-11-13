import type { TableController } from "../../utils/table-controller";

type SampleIdentifiers = {
  sampleId: string;
  sampleName?: string;
  labId?: string;
};

export function parseSampleIds(input: string): string[] {
  return [
    ...new Set(
      input
        .split(/[\r\n\t,;]+/)
        .map((id) => id.trim())
        .filter(Boolean),
    ),
  ];
}

export function matchSampleIds(ids: string[], samples: SampleIdentifiers[]) {
  const requested = new Set(ids);
  const matchedIds = new Set<string>();
  const sampleIds = new Set<string>();
  for (const sample of samples) {
    for (const value of [sample.sampleId, sample.sampleName, sample.labId]) {
      const id = value?.trim();
      if (id && requested.has(id)) {
        matchedIds.add(id);
        sampleIds.add(sample.sampleId);
      }
    }
  }
  return { sampleIds, matchedIds, unmatchedIds: ids.filter((id) => !matchedIds.has(id)) };
}

export function initSampleIdFilter(controller: TableController): void {
  const api = controller.getTable();
  const controls = document.getElementById("sample-id-filter-controls");
  const form = document.getElementById("sample-id-filter-form") as HTMLFormElement;
  const input = document.getElementById("sample-id-filter-input") as HTMLTextAreaElement;
  const modal = document.getElementById("sample-id-filter-modal");
  const clear = document.getElementById("sample-id-filter-clear") as HTMLButtonElement;
  const feedback = document.getElementById("sample-id-filter-feedback");
  const summary = document.getElementById("sample-id-filter-summary");
  const unmatched = document.getElementById("sample-id-filter-unmatched") as HTMLDetailsElement;
  const unmatchedTitle = document.getElementById("sample-id-filter-unmatched-title");
  const unmatchedList = document.getElementById("sample-id-filter-unmatched-list");
  if (
    !controls ||
    !form ||
    !input ||
    !modal ||
    !clear ||
    !feedback ||
    !summary ||
    !unmatched ||
    !unmatchedTitle ||
    !unmatchedList
  )
    return;

  const search = api.table().container().querySelector(".dt-search");
  if (search?.parentElement) {
    search.parentElement.classList.add("d-flex", "flex-wrap", "align-items-center", "gap-2");
    search.parentElement.appendChild(controls);
  }

  let activeIds: string[] = [];
  const clearFilter = () => {
    activeIds = [];
    input.value = "";
    clear.hidden = true;
    feedback.hidden = true;
    unmatched.open = false;
    unmatchedList.replaceChildren();
    api.search.fixed("sampleIds", null).draw();
  };

  modal.addEventListener("show.bs.modal", () => {
    input.value = activeIds.join("\n");
  });
  modal.addEventListener("shown.bs.modal", () => input.focus());
  clear.addEventListener("click", clearFilter);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    activeIds = parseSampleIds(input.value);
    if (activeIds.length === 0) {
      clearFilter();
      return;
    }

    // Read all rows, including other pages and rows hidden by other filters.
    const samples = api
      .rows()
      .nodes()
      .toArray()
      .map((row) => ({
        sampleId: row.id,
        sampleName: row.dataset.sampleName,
        labId: row.dataset.labId,
      }));
    const result = matchSampleIds(activeIds, samples);
    // DataTables passes the row index as a third argument, absent from its SearchInput type.
    api.search
      .fixed("sampleIds", (_text, _data, rowIndex?: number) =>
        result.sampleIds.has(api.row(rowIndex).id()),
      )
      .draw();

    const idLabel = activeIds.length === 1 ? "ID" : "IDs";
    const sampleLabel = result.sampleIds.size === 1 ? "sample" : "samples";
    summary.textContent = `${activeIds.length} unique ${idLabel} entered; ${result.matchedIds.size} matched (${result.sampleIds.size} ${sampleLabel}).`;
    feedback.hidden = false;
    clear.hidden = false;
    unmatched.hidden = result.unmatchedIds.length === 0;
    unmatched.open = false;
    const scope = feedback.dataset.scope;
    unmatchedTitle.textContent = `Not found in ${scope} (${result.unmatchedIds.length})`;
    unmatchedList.replaceChildren(
      ...result.unmatchedIds.map((id) => {
        const item = document.createElement("li");
        item.textContent = id;
        return item;
      }),
    );
  });
}
