import { JobStatusEnum } from "../enums";

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
  result: string; // Newick tree string
}

export interface ApiJobStatusSimilarity extends ApiJobStatusBase {
  result: ApiSampleSimilarity[];
}

export type ApiJobStatus =
  | ApiJobStatusNewick
  | ApiJobStatusSimilarity;

export interface ApiJobSubmission {
  id: string;
  task: string;
}