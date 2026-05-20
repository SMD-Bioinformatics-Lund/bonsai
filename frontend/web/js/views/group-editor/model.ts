import { GroupInfo } from "../../core/types";

export type EditorMode = "create" | "edit";

export class GroupEditModel {
  mode: EditorMode;
  groupId: string | null;

  displayName: string;
  description: string;

  samples: string[];
  allowedColumns: string[];

  createdAt?: string;
  modifiedAt?: string;
  sampleCount?: number;

  private constructor(mode: EditorMode) {
    this.mode = mode;
    this.groupId = null;
    this.displayName = "";
    this.description = "";
    this.samples = [];
    this.allowedColumns = [];
  }

  /* Create a fresh model */
  static initial(mode: EditorMode): GroupEditModel {
    return new GroupEditModel(mode);
  }

  /* Populate an existing model from API data */
  loadFromApi(data: GroupInfo): void {
    this.groupId = data.group_id;
    this.displayName = data.display_name;
    this.description = data.description;
    this.createdAt = data.created_at;
    this.modifiedAt = data.modified_at;
    this.sampleCount = data.sample_count;
  }
}