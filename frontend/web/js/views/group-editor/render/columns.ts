import { GroupEditModel } from "../model";
import { ManifestColumn } from "core/types";

import { ColumnItem } from "components/column-selector";

import "components/column-selector";

export function renderColumns(
  selector: HTMLElement & {items: ColumnItem[]},
  availbleColumns: ManifestColumn[],
  model: GroupEditModel
) {
    console.log("Function called!")
    if (!selector) {
      console.warn("<column-selector> not found; skipping column")
    }
    selector.items = availbleColumns.map( col => {
        return {id: col.id, label: col.label, enabled: false }
    });

    selector.addEventListener("column-selector:change", (e: any) => {
      model.allowedColumns = e.detail.items;
    })
}