import DataTable, { Api, Config } from "datatables.net-bs5";
import JSZip from "jszip";
import "datatables.net-buttons-bs5";
import "datatables.net-buttons/js/buttons.html5.mjs";
import "datatables.net-buttons/js/buttons.colVis.mjs";
import "datatables.net-datetime";
import "datatables.net-columncontrol-bs5";
import "datatables.net-searchbuilder-bs5";
import "datatables.net-searchpanes-bs5";
import "datatables.net-select-bs5";

import type {
  SampleTableRow,
  SampleTableSource,
  SummaryRow,
  TblStateCallbackFunc,
} from "../core/types";

DataTable.Buttons.jszip(JSZip);

export class TableController {
  private table: Api<SampleTableRow>;

  constructor(
    tableId: string,
    tableConfig: Config,
    private readonly source: SampleTableSource = "dom",
  ) {
    this.table = new DataTable<SampleTableRow>(`#${tableId}`, { ...tableConfig });
  }

  getTable(): Api<SampleTableRow> {
    return this.table;
  }

  getSelectedRows(): string[] {
    return this.table.rows({ selected: true }).ids().toArray();
  }

  set selectedRows(rowIds: string[]) {
    this.table.rows().deselect(); // clear current selection
    if (rowIds.length > 0) {
      this.table.rows(rowIds.map((id) => `#${id}`)).select(); // re-select rows based on state
    }
  }

  /* Remove samples from the table */
  removeSamples(rowIds: string[]): void {
    this.table
      .rows(rowIds.map((id) => `#${id}`))
      .remove()
      .draw();
  }

  // Summary updates survive deferred rendering; DOM tables use updateCells.
  updateRowData(rowIds: string[], values: Partial<SummaryRow>): boolean {
    if (this.source !== "summary") return false;
    const rows = this.table.rows(rowIds.map((id) => `#${id}`));
    rows.every(function () {
      this.data({ ...(this.data() as SummaryRow), ...values });
    });
    this.table.draw(false);
    return true;
  }

  // Update cells in server-rendered group tables without changing the page.
  updateCells(
    rowIds: string[],
    columnId: string,
    updateCell: (cell: HTMLTableCellElement) => void,
  ): HTMLTableCellElement[] {
    const table = this.table;
    const columnIndex = table
      .columns()
      .header()
      .toArray()
      .findIndex((header) => header.dataset.columnId === columnId);
    if (columnIndex === -1) {
      console.error(`Table column not found: ${columnId}`);
      return [];
    }

    const updatedCells: HTMLTableCellElement[] = [];
    rowIds.forEach((rowId) => {
      const cell = table.cell(`#${rowId}`, columnIndex);
      const node = cell.node();
      if (node) {
        updateCell(node);
        cell.invalidate("dom");
        updatedCells.push(node);
      }
    });

    if (updatedCells.length > 0) table.draw(false);
    return updatedCells;
  }
}

function manageAddToBasketBtn(selectedRows: string[]): void {
  /* Enable/ disable button for adding samples to the basket */
  const btn = document.getElementById("add-to-basket-btn") as HTMLButtonElement;
  if (btn !== null) btn.disabled = 1 > selectedRows.length;
}

function manageAnnotateQcBtn(selectedRows: string[]): void {
  /* Enable or disable bulk edit qc status button */
  const btn = document.getElementById("toggle-qc-btn") as HTMLButtonElement;
  if (btn !== null) btn.disabled = 1 > selectedRows.length;
}

function manageRemoveSamplesBtn(selectedRows: string[]): void {
  /* Enable or disable bulk edit qc status button */
  const btn = document.getElementById("remove-samples-btn") as HTMLButtonElement;
  if (btn !== null) btn.disabled = 1 > selectedRows.length;
}

function manageSelectSimilarBtn(selectedRows: string[]): void {
  /* Enable or disable search for similar samples button */
  const btn = document.getElementById("similar-samples-dropdown-btn") as HTMLButtonElement;
  if (btn !== null) btn.disabled = 1 !== selectedRows.length;
}

export function initSamplesTable(
  tableId: string,
  tableConfig: Config,
  source: SampleTableSource = "dom",
): TableController {
  const controller = new TableController(tableId, tableConfig, source);

  // add callback functions
  const funcs: TblStateCallbackFunc[] = [
    manageAddToBasketBtn,
    manageRemoveSamplesBtn,
    manageSelectSimilarBtn,
    manageAnnotateQcBtn,
  ];
  for (const callback of funcs) {
    controller.getTable().on("select deselect", () => {
      callback(controller.getSelectedRows());
    });
  }

  return controller;
}
