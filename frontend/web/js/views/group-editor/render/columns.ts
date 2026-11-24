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
    const usesDefaults = model.mode === "edit" && model.allowedColumnIds.length === 0;
    selector.items = availbleColumns.map(col => ({
      id: col.id,
      label: col.label,
      enabled: usesDefaults ? col.default_visible : model.allowedColumnIds.includes(col.id),
    }));

    selector.addEventListener("column-selector:change", (event: Event) => {
      const { items } = (event as CustomEvent<{ items: ColumnItem[] }>).detail;
      model.allowedColumnIds = items.filter((item) => item.enabled).map((item) => item.id);
    })
}
