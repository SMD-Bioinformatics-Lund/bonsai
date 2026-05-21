import { GroupEditModel } from "../model";

import "components/column-selector";

const ALL_COLUMNS = [
    {id: "sample-id", label: "Sample ID", enabled: true},
    {id: "qc-status", label: "QC status", enabled: true},
    {id: "assay", label: "Assay", enabled: true},
    {id: "assay1", label: "Assay", enabled: true},
    {id: "assay2", label: "Assay", enabled: true},
    {id: "assay3", label: "Assay", enabled: true},
    {id: "assay4", label: "Assay", enabled: true},
    {id: "assay5", label: "Assay", enabled: true},
    {id: "assay6", label: "Assay", enabled: true},
    {id: "assay7", label: "Assay", enabled: true},
    {id: "assay8", label: "Assay", enabled: true},
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