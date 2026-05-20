import { ColumnDefinition } from "../table";
import { PaginatedResponse } from "../pagination";

export interface InputCoreGroupInfo {
  display_name: string;
  description: string;
}

export interface GroupInfo {
  group_id: string;
  display_name: string;
  description: string;
  sample_count: number;
  table_columns: ColumnDefinition[];
  created_at: string;
  modified_at: string;
}

export type ApiGroupInfoResponse = PaginatedResponse<GroupInfo>;