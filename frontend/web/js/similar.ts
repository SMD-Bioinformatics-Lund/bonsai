import { ApiService, pollJob } from "./api";
import { throwSmallToast } from "./notification";
import { TableController } from "./table";
import { ApiJobStatusSimilarity } from "./types";
import { hideSpinner, showSpinner } from "./util";

export async function getSimilarSamplesAndCheckRows(
  btn: HTMLButtonElement,
  dt: TableController,
  api: ApiService,
) {
  const container = btn.closest(".similar-samples-container") as HTMLDivElement;
  const limitInput = container.querySelector(
    "#similar-samples-limit",
  ) as HTMLInputElement;
  const similarityInput = container.querySelector(
    "#similar-samples-threshold",
  ) as HTMLInputElement;
  showSpinner(container);
  const job = await api.findSimilarSamples(dt.selectedRows[0], {
    limit: parseInt(limitInput.value),
    similarity: parseFloat(similarityInput.value),
    cluster: false,
    typing_method: null,
    cluster_method: null,
  });
  // start polling for job status
  try {
    const jobFunc = async () =>
      api.checkJobStatus(job.id) as Promise<ApiJobStatusSimilarity>;
    const result = await pollJob(jobFunc, 3000);
    dt.selectedRows = result.result.map((sample) => sample.sample_id);
  } catch (error) {
    console.error("Error while checking job status:", error);
    throwSmallToast("Error while finding similar samples");
  }
  hideSpinner(container);
}
