import { GroupInfo, InputCoreGroupInfo } from "../../core/types";
import { ApiSummaryManifestResponse } from "../../core/types";

export interface GroupEditorApi {
  createGroup(data: InputCoreGroupInfo): Promise<GroupInfo>;

  updateGroup(
    groupId: string,
    data: InputCoreGroupInfo
  ): Promise<void>;

  updateAllowedColumns(
    groupId: string,
    columnIds: string[]
  ): Promise<void>;

  getGroup(groupId: string): Promise<GroupInfo>;

  getAvailableColumns(): Promise<ApiSummaryManifestResponse>
}