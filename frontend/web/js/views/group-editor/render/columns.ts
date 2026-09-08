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

    selector.addEventListener("column-selector:change", (event: Event) => {
      const { items } = (event as CustomEvent<{ items: ColumnItem[] }>).detail;
      model.allowedColumnIds = items.filter((item) => item.enabled).map((item) => item.id);
    })
}
