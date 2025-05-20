interface JobStatus {
  status: string;
  queue: string;
  result: string;
  error: string;
  submitted_at: string;
  started_at: string | null;
  finished_at: string | null;
}

enum typingMethod {
  mlst,
  cgmlst,
  ska,
  minhash,
}

enum distanceMethod {
  jaccard,
  hamming,
}

enum clusterMethod {
  single,
  complete,
  average,
  neighbor_joining,
  MSTreeV2,
}

interface ApiJobSubmission {
  id: string;
  task: string;
}

interface ApiClusterInput {
  sampleIds: string[];
  distance: distanceMethod;
  method: clusterMethod;
}

interface ApiFindSimilarInput {
  limit: number | null; // number of samples to return
  similarity: number; // min similarity
  cluster: boolean; // cluster similar samples
  typing_method: typingMethod | null; // use typing method if cluster is true
  cluster_method: clusterMethod | null; // use cluster method if cluster is true
}

interface ColumnDefinition {
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

interface GroupInfo {
  group_id: string;
  display_name: string;
  description: string;
  included_samples: string[];
  table_columns: ColumnDefinition[];
  created_at: string;
  modified_at: string;
}

type TblStateCallbackFunc = (selectedRows: string[]) => void