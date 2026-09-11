import { PaginatedResponse } from "../pagination";

export interface ApiGetSamplesDetailsInput {
  sid: string[];
  fields?: string[];
  limit: number | null;
  offset?: number;
  // Kept while older callers are migrated to the current summary API.
  skip?: number;
  prediction_result?: boolean;
  qc?: boolean;
}

export interface SamplesDetails {
  sample_id: string;
  external_sample_id?: string;
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

export interface ManifestColumn {
  id: string,
  type: string,
  label: string,
  source: string,
  default_visible: boolean,
  filterable: boolean,
  sortable: boolean,
}

export interface ApiSummaryManifestResponse {
  columns: ManifestColumn[]
  etag: string
  version: string
}

export type ApiSampleDetailsResponse =
  PaginatedResponse<SamplesDetails>;
