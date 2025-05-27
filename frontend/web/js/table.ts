import DataTable from "datatables.net-bs5";
import 'datatables.net-datetime'
import 'datatables.net-searchbuilder-bs5';
import 'datatables.net-select-bs5';

import { ApiService } from "./api";
import { ApiFindSimilarInput, ApiJobSubmission, TblStateCallbackFunc } from "./types";


export class TableStateManager {
  private tableId: string;
  private selectedRows: Set<string>;
  private rowSelectionListeners: Set<TblStateCallbackFunc>;

  constructor(tableId: string) {
    this.tableId = tableId;
    this.selectedRows = new Set<string>();
    this.rowSelectionListeners = new Set();
    this.loadState();
  }

  toggleRow(rowId: string): void {
    if (this.selectedRows.has(rowId)) {
      this.selectedRows.delete(rowId);
    } else {
      this.selectedRows.add(rowId);
    }
    this.saveState();
    this.notifyChange();
  }

  isSelected(rowId: string): boolean {
    return this.selectedRows.has(rowId);
  }

  getSelected(): string[] {
    return Array.from(this.selectedRows);
  }

  setSelected(rowIds: string[]): void {
    this.selectedRows = new Set(rowIds);
    this.saveState();
    this.notifyChange();
  }

  clearSelection(): void {
    this.selectedRows.clear();
    this.saveState();
    this.notifyChange();
  }

  onSelection(callback: TblStateCallbackFunc): void {
    this.rowSelectionListeners.add(callback);
  }

  offSelection(callback: TblStateCallbackFunc): void {
    this.rowSelectionListeners.delete(callback);
  }

  private notifyChange(): void {
    const selected = this.getSelected()
    for (const callback of this.rowSelectionListeners) {
      callback(selected);
    }
  }

  private saveState(): void {
    localStorage.setItem(this.storageKey, JSON.stringify(this.getSelected()));
  }

  private loadState(): void {
    const state = localStorage.getItem(this.storageKey);
    if (state) {
      try {
        const ids = JSON.parse(state) as string[];
        this.selectedRows = new Set(ids);
      } catch (e) {
        console.error("Failed to parse saved table state", e);
      }
    }
  }

  private get storageKey(): string {
    return `${this.tableId}_selected_rows`;
  }
}

export class TableController {
  private table: any;
  //private tableState: TableStateManager;

  constructor(tableId: string, tableConfig: any) {
    //this.tableState = new TableStateManager(tableId);
    this.table = new DataTable<string>(`#${tableId}`, { ...tableConfig });

    // listen for row selection changes in DataTable
    // this.table.on('select', this.handleRowSelectionChange.bind(this));
    // this.table.on('deselect', this.handleRowSelectionChange.bind(this));
    // synchronize selection with the state manager
    //this.tableState.onSelection(selectedRows => this.synchronizeSelection(selectedRows));
  }

  // private synchronizeSelection(selectedRows: string[]): void {
  //   //const selectedRows = this.tableState.getSelected();
  //   this.table.rows().deselect(); // clear current selection
  //   if (selectedRows.length > 0) {
  //     this.table.rows(selectedRows).select(); // re-select rows based on state
  //   }
  // }

  // private handleRowSelectionChange(): void {
  //   const rowIds: string[] = Array.from(this.table.rows('.selected').ids());
  //   this.tableState.setSelected(rowIds);
  // }

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


  // getStateManager(): TableStateManager {
  //   return this.tableState;
  // }
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
  //const table = new DataTable<string>(`#${tableId}`, { ...tableConfig });

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
  // return {
  //   table: controller.getTable(), 
  //   tblState: controller.getStateManager(),
  // }
}

