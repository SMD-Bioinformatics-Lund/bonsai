import DataTable from "datatables.net-bs5";
import 'datatables.net-datetime'
import 'datatables.net-buttons-bs5';
import 'datatables.net-buttons/js/buttons.html5.mjs';
import 'datatables.net-select-bs5';
import 'datatables.net-searchbuilder-bs5';

import { TblStateCallbackFunc } from "./types";

export class TableController {
  private table: any;

  constructor(tableId: string, tableConfig: any) {
    this.table = new DataTable<string>(`#${tableId}`, { ...tableConfig });
  }

  getTable(): any {
    return this.table;
  }

  get selectedRows(): string[] {
    return this.table.rows('.selected').ids().toArray();
  }

  set selectedRows(rowIds: string[]) {
    this.table.rows().deselect(); // clear current selection
    if (rowIds.length > 0) {
      this.table.rows(rowIds.map(id => `#${id}`)).select(); // re-select rows based on state
    }
  }
}

function manageAddToBasketBtn(selectedRows: string[]): void {
  /* Enable/ disable button for adding samples to the basket */
  const btn = document.getElementById("add-to-basket-btn") as HTMLButtonElement;
  console.log(selectedRows)
  if ( btn !== null) btn.disabled = 1 > selectedRows.length
}

function manageAnnotateQcBtn(selectedRows: string[]): void {
  /* Enable or disable bulk edit qc status button */
  const btn = document.getElementById("toggle-qc-btn") as HTMLButtonElement;
  if ( btn !== null) btn.disabled = 1 > selectedRows.length
}

function manageRemoveSamplesBtn(selectedRows: string[]): void {
  /* Enable or disable bulk edit qc status button */
  const btn = document.getElementById("remove-samples-btn") as HTMLButtonElement;
  if ( btn !== null) btn.disabled = 0 > selectedRows.length
}

function manageSelectSimilarBtn(selectedRows: string[]): void {
  /* Enable or disable search for similar samples button */
  const btn = document.getElementById("select-similar-samples-btn") as HTMLButtonElement;
  if ( btn !== null) btn.disabled = 1 !== selectedRows.length
}

export function initializeSamplesTable(tableId: string, tableConfig: any): any {
  const controller = new TableController(tableId, tableConfig);

  // add callback functions
  const funcs: TblStateCallbackFunc[] = new Array(manageAddToBasketBtn, manageRemoveSamplesBtn, manageSelectSimilarBtn)
  for (const callback of funcs ){
    //controller.getStateManager().onSelection(callback)
    controller.getTable().on('select deselect', (e, dt, type, indexes) => {
      const selected: string[] = dt.rows('.selected').ids()
      callback(selected)
    });
  }

  return controller;
}

