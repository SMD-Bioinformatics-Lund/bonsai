import { initSampleTable, updateSampleQc } from "../../web/js/views/groups-view/sample-table";
import type { TableController } from "../../web/js/utils/table-controller";

let table: TableController | null;
Object.assign(window, {
  tableTest: {
    async start() {
      table = await initSampleTable(document.querySelector("table"), {
        select: true,
        pageLength: 10,
        order: [],
        layout: {
          topStart: { buttons: [{ extend: "selectAll", selectorModifier: { search: "applied" } }] },
        },
      });
    },
    api: () => table?.getTable(),
    select: (ids: string[]) => {
      table.selectedRows = ids;
    },
    selected: () => table.getSelectedRows(),
    qc: () =>
      updateSampleQc(
        table,
        { status: "failed", action: "resequence", comment: "Needs another run" },
        table.getSelectedRows(),
      ),
  },
});
