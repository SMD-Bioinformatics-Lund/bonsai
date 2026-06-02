import DataTable from "datatables.net-bs5";

export async function initVariantsTable(tableId: string, search: boolean = true): Promise<any> {
  if (document.getElementById(tableId) === null) {
    console.warn(`No table with id: ${tableId} found, cant create datatable`);
    return;
  }

  return new DataTable(tableId, {
    paging: false,
    select: false,
    searching: search,
  });
}

// Expose globally for templates that call it directly
(window as any).initVariantsTable = initVariantsTable;
