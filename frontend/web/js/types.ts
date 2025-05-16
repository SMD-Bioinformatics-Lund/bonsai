interface JobStatus {
    status: string
    queue: string
    result: string
    error: string
    submitted_at: string
    started_at: string | null
    finished_at: string | null
}

enum typingMethod { mlst, cgmlst, ska, minhash }

enum distanceMethod { jaccard, hamming }

enum clusterMethod { single, complete, average, neighbor_joining, MSTreeV2 }

interface ApiClusterInput {
    sampleIds: string[]
    distance: distanceMethod
    method: clusterMethod
}