export enum JobStatusEnum {
  QUEUED = "queued",
  STARTED = "started",
  DEFERRED = "deferred",
  FINISHED = "finished",
  STOPPED = "stopped",
  SCHEDULED = "scheduled",
  CANCELED = "canceled",
  FAILED = "failed",
}

export enum TypingMethod {
  MLST = "mlst",
  CGMLST = "cgmlst",
  SKA = "ska",
  MINHASH = "minhash",
}

export enum DistanceMethod {
  JACCARD = "jaccard",
  HAMMING = "hamming",
}

export enum ClusterMethod {
  SINGLE = "single",
  COMPLETE = "complete",
  AVERAGE = "average",
  NEIGHBORJOINING = "neighbor_joining",
  MSTREE2 = "MSTreeV2",
}