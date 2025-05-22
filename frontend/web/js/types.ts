import { DistanceMethod, ClusterMethod, TypingMethod, JobStatusEnum } from "./constants"

export interface JobStatus {
  status: JobStatusEnum;
  queue: string;
  result: string;
  error: string;
  submitted_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ApiJobSubmission {
  id: string;
  task: string;
}

export interface ApiClusterInput {
  sampleIds: string[];
  distance: DistanceMethod;
  method: ClusterMethod;
}

export interface ApiFindSimilarInput {
  limit: number | null; // number of samples to return
  similarity: number; // min similarity
  cluster: boolean; // cluster similar samples
  typing_method: TypingMethod | null; // use typing method if cluster is true
  cluster_method: ClusterMethod | null; // use cluster method if cluster is true
}

export interface ApiGetSamplesDetailsInput {
  sid: string[];
  limit: number;
  skip: number;
  prediction_result: boolean;
  qc: boolean;
}

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

export interface GroupInfo {
  group_id: string;
  display_name: string;
  description: string;
  included_samples: string[];
  table_columns: ColumnDefinition[];
  created_at: string;
  modified_at: string;
}

export interface SamplesDetails {
  sample_id: string;
  sample_name: string
  lims_id: string
  assay: string
  created_at: string
}

export interface ApiSampleDetailsResponse {
  data: SamplesDetails[]
  records_total: number
  records_filtered: number
}

export type CallbackFunc = (ids: string[]) => void
export type TblStateCallbackFunc = (selectedRows: string[]) => void