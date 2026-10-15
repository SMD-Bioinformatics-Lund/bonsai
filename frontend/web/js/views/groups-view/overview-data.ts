import type { Config } from "datatables.net-bs5";

interface RenderedCell {
  display: string;
  sort?: string;
  filter?: string;
}

export async function loadOverviewTable(table: HTMLTableElement): Promise<Config> {
  const response = await fetch(table.dataset.source, { credentials: "same-origin" });
  if (!response.ok) throw new Error(`Sample overview request failed (${response.status})`);
  const data = await response.json();
  const headers = Array.from(table.querySelectorAll<HTMLTableCellElement>("thead th"));
  const columns = headers.map((header) => {
    const index = data.columns.findIndex((column) => column.id === header.dataset.columnId);
    if (index === -1) throw new Error(`Missing summary column: ${header.dataset.columnId}`);
    const column = data.columns[index];
    header.dataset.filterable = String(column.filterable);
    return {
      data: `cells.${index}`,
      orderable: column.sortable,
      searchable: column.searchable,
      visible: column.visible,
      render: (cell: RenderedCell, type: string) =>
        (type === "sort" || type === "type" ? cell.sort : type === "filter" ? cell.filter : undefined)
        ?? cell.display,
    };
  });
  return {
    data: data.rows, columns, rowId: "sample_id", deferRender: true,
    createdRow: (row, _data, index) => {
      row.dataset.testId = `sample-row-${index + 1}`;
    },
  };
}
