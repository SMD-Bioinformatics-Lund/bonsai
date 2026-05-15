export type EditorMode = "create" | "edit";

export interface GroupEditModel {
  mode: EditorMode;
  groupId: string | null;

  displayName: string;
  description: string;

  createdAt?: string;
  modifiedAt?: string;
  sampleCount?: number;
}