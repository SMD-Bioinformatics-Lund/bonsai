import { GroupEditModel } from "../model";
import { ManifestColumn } from "core/types";

import { ColumnItem } from "components/column-selector";

import "components/column-selector";

export function renderColumns(
  selector: HTMLElement & {items: ColumnItem[]},
  availbleColumns: ManifestColumn[],
  model: GroupEditModel
) {
    if (!selector) {
      console.warn("<column-selector> not found; skipping column")
    }
    selector.items = availbleColumns.map( col => {
        return {id: col.id, label: col.label, enabled: false || model.allowedColumnIds.includes(col.id)}});

    selector.addEventListener("column-selector:change", (e: any) => {
      model.allowedColumnIds = e.detail.items;
    })
}