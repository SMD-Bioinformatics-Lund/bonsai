import type { Config } from "datatables.net-bs5";
import type { ApiSampleQcStatus } from "../../core/types";
import { initTooltip } from "../../utils/notification";
import { initSamplesTable, TableController } from "../../utils/table-controller";
import { loadOverviewTable, renderSummaryCell } from "./sample-table-data";

export function showSampleTable(table?: TableController): void {
  document.getElementById("sample-table-loading")?.remove();
  document.getElementById("sample-table-container")?.classList.remove("d-none");
  table?.getTable().columns.adjust();
}

function showLoadingFailure(error: unknown): void {
  console.error("Unable to load overview samples", error);
  const loading = document.getElementById("sample-table-loading");
  if (!loading) return;
  const message = document.createElement("span");
  message.textContent = "Unable to load samples. ";
  const retry = document.createElement("button");
  retry.className = "btn btn-sm btn-outline-secondary ms-2";
  retry.textContent = "Retry";
  retry.onclick = () => window.location.reload();
  loading.replaceChildren(message, retry);
}

export async function initSampleTable(
  element: HTMLTableElement,
  baseConfig: Config,
): Promise<TableController | null> {
  const source = element.dataset.source ? "summary" : "dom";
  let dataConfig: Config = {};
  if (source === "summary") {
    try {
      dataConfig = await loadOverviewTable(element);
    } catch (error) {
      showLoadingFailure(error);
      return null;
    }
  }
  const headers = Array.from(element.querySelectorAll<HTMLTableCellElement>("thead th"));
  const config: Config = {
    ...baseConfig,
    ...dataConfig,
    searchBuilder: {
      columns: headers.flatMap((header, index) =>
        header.dataset.filterable === "true" ? [index] : [],
      ),
    },
  };
  if (element.dataset.defaultSort) {
    const sortIndex = headers.findIndex(
      (header) => header.dataset.columnId === element.dataset.defaultSort,
    );
    if (sortIndex !== -1) config.order = [[sortIndex, "desc"]];
  }

  let table: TableController;
  try {
    table = initSamplesTable(element.id, config, source);
  } catch (error) {
    showSampleTable();
    throw error;
  }
  showSampleTable(table);
  const initTableTooltips = () => initTooltip(element);
  table.getTable().on("draw", initTableTooltips);
  initTableTooltips();
  return table;
}

export function updateSampleQc(
  table: TableController,
  status: ApiSampleQcStatus,
  sampleIds: string[],
): void {
  if (table.updateRowData(sampleIds, { qc_status: status })) return;
  const cells = table.updateCells(sampleIds, "qc_status", (cell) => {
    cell.innerHTML = String(
      renderSummaryCell({ renderer: "qc_status_renderer" }, status, "display", ""),
    );
  });
  cells.forEach((cell) => initTooltip(cell));
}
