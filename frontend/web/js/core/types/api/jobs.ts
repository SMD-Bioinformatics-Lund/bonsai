import { JobStatusEnum } from "../enums";

interface ApiSimilarityMatch {
  sample_id: string;
  signature_checksum: string;
  containment: number;
  jaccard_similarity: number;
  max_containment: number;
}

interface ApiSimilaritySearchResult {
  query: string;
  ksize: number;
  moltype: string;
  search_time: number;
  matches: ApiSimilarityMatch[];
}

export interface ApiJobStatusBase {
  status: JobStatusEnum;
  queue: string;
  error: string | null;
  submitted_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ApiJobStatusNewick extends ApiJobStatusBase {
  result: string; // Newick tree string
}

export interface ApiJobStatusSimilarity extends ApiJobStatusBase {
  result: ApiSimilaritySearchResult;
}

export type ApiJobStatus =
  | ApiJobStatusNewick
  | ApiJobStatusSimilarity;

export interface ApiJobSubmission {
  id: string;
  task: string;
}
