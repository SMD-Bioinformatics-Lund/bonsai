import { GroupEditModel } from "../model";

import "components/column-selector";

const ALL_COLUMNS = [
    {id: "sample-id", label: "Sample ID", enabled: true},
    {id: "qc-status", label: "QC status", enabled: true},
    {id: "assay", label: "Assay", enabled: true},
];


export function renderColumns(
  selector: HTMLElement,
  model: GroupEditModel
) {
    console.log("Function called!")
    if (!selector) {
      console.warn("<column-selector> not found; skipping column")
    }
    //selector.items = model.allowedColumns;
    selector.items = ALL_COLUMNS;

    selector.addEventListener("column-selector:change", (e: any) => {
      model.allowedColumns = e.detail.items;
    })
}