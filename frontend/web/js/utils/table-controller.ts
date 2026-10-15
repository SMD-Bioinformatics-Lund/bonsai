import DataTable, { Api, Config } from "datatables.net-bs5";
import JSZip from "jszip";
import "datatables.net-buttons-bs5";
import "datatables.net-buttons/js/buttons.html5.mjs";
import "datatables.net-buttons/js/buttons.colVis.mjs";
import "datatables.net-datetime";
import "datatables.net-columncontrol-bs5";
import "datatables.net-datetime";
import "datatables.net-searchbuilder-bs5";
import "datatables.net-searchpanes-bs5";
import "datatables.net-select-bs5";

import { TblStateCallbackFunc } from "../core/types";

DataTable.Buttons.jszip(JSZip);

export class TableController {
  private table: Api<string>;

  constructor(tableId: string, tableConfig: Config) {
    this.table = new DataTable<string>(`#${tableId}`, { ...tableConfig });
  }

  getTable(): Api<string> {
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

  // Deferred rows need their source cells updated even before they have DOM nodes.
  updateCells(
    rowIds: string[],
    columnId: string,
    updateCell: (cell: HTMLTableCellElement) => void,
  ): HTMLTableCellElement[] {
    const columnIndex = this.table
      .columns()
      .header()
      .toArray()
      .findIndex((header) => header.dataset.columnId === columnId);
    if (columnIndex === -1) {
      console.error(`Table column not found: ${columnId}`);
      return [];
    }

    const updatedCells: HTMLTableCellElement[] = [];
    const deferred = !!this.table.table().node().dataset.source;
    let changed = false;
    rowIds.forEach((rowId) => {
      const cell = this.table.cell(`#${rowId}`, columnIndex);
      if (!cell.any()) return;
      const node = cell.node() || (deferred ? document.createElement("td") : null);
      if (node) {
        updateCell(node);
        if (deferred) cell.data({ display: node.innerHTML });
        else cell.invalidate("dom");
        updatedCells.push(node);
        changed = true;
      }
    });

    if (changed) this.table.draw(false);
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
  if (btn !== null) btn.disabled = 0 > selectedRows.length;
}

function manageSelectSimilarBtn(selectedRows: string[]): void {
  /* Enable or disable search for similar samples button */
  const btn = document.getElementById("similar-samples-dropdown-btn") as HTMLButtonElement;
  if (btn !== null) btn.disabled = 1 !== selectedRows.length;
}

export function initSamplesTable(tableId: string, tableConfig: Config): TableController {
  const controller = new TableController(tableId, tableConfig);

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
