import {
  DistanceMethod,
  ClusterMethod,
  TypingMethod,
} from "../enums";

export interface ApiClusterInput {
  sampleIds: string[];
  distance: DistanceMethod;
  method: ClusterMethod;
}

export interface ApiUnplacedSample {
  sample_id: string;
  label: string;
  reason: string;
}

export interface ApiAlleleClusterValidation {
  can_cluster: boolean;
  notice: string | null;
  unplaced_samples: ApiUnplacedSample[];
}

export type ApiAlleleClusterValidations = Record<"mlst" | "cgmlst", ApiAlleleClusterValidation>;

export interface ApiFindSimilarInput {
  limit: number | null;
  narrow_to_sample_ids: string[] | null;
  similarity: number;
  cluster: boolean;
  typing_method: TypingMethod | null;
  cluster_method: ClusterMethod | null;
}
