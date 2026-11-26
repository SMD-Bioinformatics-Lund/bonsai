import { GroupEditModel } from "../model";
import { ManifestColumn } from "core/types";
import { ColumnSelector } from "components/column-selector";

import "components/column-selector";

export function renderColumns(
  selector: ColumnSelector,
  availableColumns: ManifestColumn[],
  model: GroupEditModel
): string[] {
  const allAllowed = model.mode === "edit" && model.allowedColumnIds.length === 0;
  selector.items = availableColumns.map(col => ({
    id: col.id,
    label: col.label,
    enabled: allAllowed || model.allowedColumnIds.includes(col.id),
  }));
  return selector.items.filter(item => item.enabled).map(item => item.id);
}
