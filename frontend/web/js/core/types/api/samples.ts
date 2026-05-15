import { PaginatedResponse } from "../pagination";

export interface ApiGetSamplesDetailsInput {
  sid: string[];
  limit: number;
  skip: number;
  prediction_result: boolean;
  qc: boolean;
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

export type ApiSampleDetailsResponse =
  PaginatedResponse<SamplesDetails>;