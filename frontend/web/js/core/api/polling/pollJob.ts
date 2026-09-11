import { ApiJobStatus } from "core/types";
import { JobStatusEnum } from "core/types/enums";

export async function pollJob<T extends ApiJobStatus>(
  checkJobFn: () => Promise<T>,
  waitTime: number,
  maxRetries = 100,
): Promise<T> {
  let retries = 0;
  let result = await checkJobFn();

  while (isJobRunning(result)) {
    if (retries++ >= maxRetries) {
      throw new Error(`Polling exceeded maximum retries (${maxRetries})`);
    }
    await wait(waitTime);
    result = await checkJobFn();
  }

  return result;
}

function isJobRunning(job: ApiJobStatus): boolean {
  if (job.status === JobStatusEnum.FINISHED) return false;
  if (job.status === JobStatusEnum.FAILED) {
    throw new Error(`Job failed`);
  }
  return true;
}

function wait(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms));
}