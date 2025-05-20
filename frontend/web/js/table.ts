import DataTable from "datatables.net-bs5";
import 'datatables.net-datetime'
import 'datatables.net-searchbuilder-bs5';
import 'datatables.net-select-bs5';

import { ApiService } from "./api";


class TableStateManager {
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

export async function getSimilarSamplesV2(
  tableState: TableStateManager,
  api: ApiService,
): Promise<ApiJobSubmission | boolean> {
  const sampleId = tableState.getSelected()[0];
  const limitInput = document.getElementById(
    "similar-samples-limit",
  ) as HTMLInputElement;
  const similarityInput = document.getElementById(
    "similar-samples-threshold",
  ) as HTMLInputElement;
  const searchParams: ApiFindSimilarInput = {
    limit: Number(limitInput.value),
    similarity: Number(similarityInput.value),
    cluster: false,
    typing_method: null,
    cluster_method: null,
  };
  try {
    return api.findSimilarSamples(sampleId, searchParams);
  } catch (error) {
    console.error("Error:", error);
    return false;
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

export function initializeSamplesTable(tableId: string, tableConfig: any) {
  const tblState = new TableStateManager(tableId)
  const table = new DataTable(tableId, {...tableConfig});

  table.on('select', (e, dt, type, indexes) => {
    const rowIds: string[] = Array.from(dt.rows('.selected').ids())
    tblState.setSelected(rowIds)}
  )
  table.on('deselect', (e, dt, type, indexes) => {
    const rowIds: string[] = Array.from(dt.rows('.selected').ids())
    tblState.setSelected(rowIds)}
  )

  // add callback functions
  const funcs: TblStateCallbackFunc[] = new Array(manageAddToBasketBtn, manageRemoveSamplesBtn, manageSelectSimilarBtn)
  for (const callback of funcs ){
    tblState.onSelection(callback)
  }

  return {table, tblState}
}

