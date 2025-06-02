// Description: Functions to handle sample-related operations such as finding similar samples and adding selected samples to a group.

import { ApiService, pollJob } from "./api";
import { emitEvent } from "./event-bus";
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

export function addSelectedSamplesToGroup(element: HTMLElement, table: TableController, api: ApiService): void {
  const groupId = element.getAttribute("data-bi-group-id");
  if (groupId === null) return;

  if (table.selectedRows.length === 0) {
    throwSmallToast("No samples selected", "warning");
    return;
  }

  table.selectedRows.forEach(sampleId => {
    api.addSampleToGroup(groupId, sampleId)
      .catch(error => {
        console.error(`Error adding ${sampleId} to group:`, error);
        throwSmallToast(`Error adding ${sampleId} to group`, "error");
      });
  });
  throwSmallToast(`Added ${table.selectedRows.length} samples to group`, "success");
};

export function removeSamplesFromGroup(groupId: string, table: TableController, api: ApiService): void {
}

export function deleteSelectedSamples(table: TableController, api: ApiService): void {
  const selectedSamples = table.selectedRows;
  api.deleteSamples(selectedSamples)
    .then(() => {
      throwSmallToast(`Deleted ${selectedSamples.length} samples`, "success");
      table.removeSamples(selectedSamples);
      table.selectedRows = []; // clear selection after deletion
      // Notify other components or update UI as needed
      emitEvent('samples:deleted', { sampleIds: selectedSamples });
    }).catch(error => {
      console.error("Error removing samples from database", error);
      throwSmallToast("Error when removing samples", "error");
    });
}