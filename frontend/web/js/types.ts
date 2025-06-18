import {
  DistanceMethod,
  ClusterMethod,
  TypingMethod,
  JobStatusEnum,
} from "./constants";

interface ApiSampleSimilarity {
  sample_id: string;
  similarity: number;
}

export interface ApiJobStatusBase {
  status: JobStatusEnum;
  queue: string;
  error: string;
  submitted_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ApiJobStatusNewick extends ApiJobStatusBase {
  result: string; // result is a Newick string for tree visualization
}

export interface ApiJobStatusSimilarity extends ApiJobStatusBase {
  result: ApiSampleSimilarity[]; // result is an array of sample similarities
}

export type ApiJobStatus = ApiJobStatusNewick | ApiJobStatusSimilarity;

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
  sample_name: string;
  lims_id: string;
  assay: string;
  created_at: string;
}

export interface ApiSampleQcStatus {
  status: string;
  action: string | null;
  comment: string | null;
}

export interface ApiSampleDetailsResponse {
  data: SamplesDetails[];
  records_total: number;
  records_filtered: number;
}

export interface ApiUserInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  disabled: boolean;
  roles: string[];
  authentication_method: string;
}

export type CallbackFunc = (ids: string[]) => void;
export type TblStateCallbackFunc = (selectedRows: string[]) => void;
