import type { ApiSampleQcStatus } from "./api/samples";

export interface ColumnDefinition {
  id: string;
  label: string;
  path: string;
  type: string;
  hidden: boolean;
  sortable: boolean;
  filterable: boolean;
  filter_type: string;
  filter_param: string;
}

export interface SummaryGroup {
  id: string;
  display_name: string;
}

export interface SummaryTag {
  label: string;
  severity: string;
  description?: string;
}

export interface SummaryComment {
  comment: string;
  username: string;
  displayed: boolean;
}

export interface SummaryRow {
  sample_id: string;
  qc_status?: ApiSampleQcStatus;
  groups?: SummaryGroup[];
  tags?: SummaryTag[];
  comments?: SummaryComment[];
  [column: string]: unknown;
}

export interface SummaryColumn {
  id: string;
  type: string;
  renderer: string;
  sortable: boolean;
  searchable: boolean;
  filterable: boolean;
  visible: boolean;
}

export type SampleTableRow = SummaryRow | string[];
export type SampleTableSource = "summary" | "dom";
