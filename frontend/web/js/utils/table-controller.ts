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
  private table: Api<any>;

  constructor(tableId: string, tableConfig: Config) {
    this.table = new DataTable<any>(`#${tableId}`, { ...tableConfig });
  }

  getTable(): Api<any> {
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

  // Return false for legacy tables backed by DOM arrays, which still need the
  // cell-update path. Object-backed tables retain updates before rendering.
  updateRowData(rowIds: string[], values: Record<string, unknown>): boolean {
    const rows = this.table.rows(rowIds.map((id) => `#${id}`));
    const data = rows.data().toArray();
    if (!data.length || data.some((row) => Array.isArray(row))) return false;
    rows.every(function () {
      this.data({ ...this.data(), ...values });
    });
    this.table.draw(false);
    return true;
  }

  // Update cells backed by the existing DOM and redraw without changing page.
  // Temporary solution to get this up and running. Not carefully integrated in the
  // existing systems so might not be the best way to do it. / JW 260915
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
    rowIds.forEach((rowId) => {
      const cell = this.table.cell(`#${rowId}`, columnIndex);
      const node = cell.node();
      if (node) {
        updateCell(node);
        cell.invalidate("dom");
        updatedCells.push(node);
      }
    });

    if (updatedCells.length > 0) this.table.draw(false);
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
