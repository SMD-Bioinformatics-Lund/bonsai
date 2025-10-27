// Description: Functions to handle sample-related operations such as finding similar samples and adding selected samples to a group.

import { ApiService, pollJob, wait } from "../api";
import { emitEvent } from "../utils/event-bus";
import { throwSmallToast } from "../utils/notification";
import { TableController } from "../utils/table-controller";
import { ClusterMethod, TypingMethod } from "../constants";
import { ApiFindSimilarInput } from "../types";
import {
  ApiJobStatusNewick,
  ApiJobStatusSimilarity,
  ApiJobSubmission,
  ApiSampleQcStatus,
} from "../types";
import { ApiJobTimeout } from "../constants";
import SpinnerElement from "../components/spinner-element";
import { hideSpinner, showSpinner } from "./spinner-actions";


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
  const job = await api.findSimilarSamples(dt.getSelectedRows()[0], {
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

export function removeSamplesFromGroup(
  groupId: string,
  table: TableController,
  api: ApiService,
): void {
  const selectedSamples = table.getSelectedRows();
  if (selectedSamples.length === 0) {
    throwSmallToast("No samples selected", "warning");
    return;
  }
  api
    .removeSamplesFromGroup(groupId, selectedSamples)
    .then(() => {
      emitEvent("samples:removed-from-group", {}); // Notify other components or update UI as needed
      table.removeSamples(selectedSamples);
      table.selectedRows = []; // clear selection after deletion
      throwSmallToast(
        `Removed ${selectedSamples.length} samples from group`,
        "success",
      );
    })
    .catch((error) => {
      console.error(
        `Error removing ${selectedSamples.length} from group:`,
        error,
      );
      throwSmallToast(
        `Error removing ${selectedSamples.length} from group`,
        "error",
      );
    });
}

export function deleteSelectedSamples(
  table: TableController,
  api: ApiService,
): void {
  const selectedSamples = table.getSelectedRows();
  api
    .deleteSamples(selectedSamples)
    .then(() => {
      throwSmallToast(`Deleted ${selectedSamples.length} samples`, "success");
      table.removeSamples(selectedSamples);
      table.selectedRows = []; // clear selection after deletion
      // Notify other components or update UI as needed
      emitEvent("samples:deleted", { sampleIds: selectedSamples });
    })
    .catch((error) => {
      console.error("Error removing samples from database", error);
      throwSmallToast("Error when removing samples", "error");
    });
}

/* Setup listeners and functionality of set Qc status form */
export function initSetSampleQc(
  getSampleIds: () => string[],
  submitQc: (sampleId: string, data: ApiSampleQcStatus) => Promise<void>,
  onStatusChange: (status: ApiSampleQcStatus) => void,
  form: HTMLElement,
) {
  const passedQcBtn = form.querySelector("#passed-qc-btn") as HTMLButtonElement;
  const failedQcBtn = form.querySelector("#failed-qc-btn") as HTMLButtonElement;
  const failedQcAction = form.querySelector(
    "#failed-qc-action",
  ) as HTMLSelectElement;
  const failedQcComment = form.querySelector(
    "#failed-qc-comment-container",
  ) as HTMLTextAreaElement;
  const submitBtn = form.querySelector("#qc-submit-btn") as HTMLButtonElement;

  const hideQcRejection = () => {
    failedQcAction.disabled = true;
    failedQcAction.hidden = true;
    failedQcAction.value = "0";
    failedQcComment.hidden = true;
  };

  const showQcRejection = () => {
    failedQcAction.disabled = false;
    failedQcAction.hidden = false;
    failedQcComment.hidden = false;
  };

  passedQcBtn.onclick = hideQcRejection;
  failedQcBtn.onclick = showQcRejection;
  form.onchange = () => {
    const qcStatus = form.querySelector(
      "input[name='qc-validation']:checked",
    ) as HTMLInputElement;
    submitBtn.disabled =
      failedQcAction.value === "" && qcStatus.value === "failed";
  };

  // add submit function
  submitBtn.onclick = (e: Event) => {
    e.preventDefault();
    const sampleIds = getSampleIds();
    const status = form.querySelector(
      "input[name='qc-validation']:checked",
    ) as HTMLInputElement;
    const isFailed: boolean = status.value === "failed";
    const qcStatus: ApiSampleQcStatus = {
      status: status.value,
      action: isFailed ? failedQcAction.value : null,
      comment: isFailed ? failedQcComment.querySelector("textarea").value : "",
    };
    sampleIds.forEach((sampleId) => {
      submitQc(sampleId, qcStatus).catch((e: Error) => {
        console.error(`Error updating QC of sample: ${sampleId}`, e);
        throwSmallToast(`Failed to update QC of sample ${sampleId}`, "error");
      });
      wait(100);
    });
    onStatusChange(qcStatus);  // update displayed content function
    throwSmallToast(`Updated Qc of ${sampleIds.length} sample`, "success");
  };
}

/* Find samples similar to the given sample id, cluster them and plot as dendrogram */
export async function findAndClusterSimilarSamples(
  sampleId: string,
  api: ApiService,
) {
  const container = document.getElementById("similar-samples-card");
  const spinner = container.querySelector("spinner-element") as SpinnerElement;
  spinner?.show()
  const searchParams: ApiFindSimilarInput = {
    limit: 10,
    similarity: 0.9,
    cluster: true,
    typing_method: TypingMethod.MINHASH,
    cluster_method: ClusterMethod.SINGLE,
  };
  // queue similar samples job
  const job = await api.findSimilarSamples(sampleId, searchParams);
  console.log("Waiting for the following job ID:", job.id);
  try {
    const jobFunc = async () =>
      api.checkJobStatus(job.id) as Promise<ApiJobStatusNewick>;
    const jobResult = await pollJob(jobFunc, 3000, 40);
    console.log("Here is the find similar result:", jobResult.result);

    // draw dendrogam in container element
    drawDendrogram("#tree-body", jobResult.result, sampleId);
  } catch (error) {
    container.hidden = true;
    throwSmallToast("Error while finding similar samples");
    console.error("Error while checking job status:", error);
    throw error;
  }
  finally {
    spinner?.hide()
  }
}

/* Draw dendrogram from Newick string */
export function drawDendrogram(
  containerSelector: string,
  newick: string,
  sampleId: string,
): void {
  const container = document.querySelector(containerSelector);
  if (!container) {
    console.error(`Container element not found: ${containerSelector}`);
    return;
  }
  if (!(window as any).TidyTree) {
    console.error('TidyTree library is not loaded');
    return;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tree = new (window as any).TidyTree(newick, {
    parent: container,
    layout: "vertical",
    type: "dendrogram",
    mode: "square",
    ruler: false,
    leafLabels: true,
    margin: [10, 10, 80, 10],
  });

  tree
    .search((d: { data: { id: string } }) => d.data.id.includes(sampleId))
    .selectAll("circle")
    .style("fill", "steelblue")
    .attr("r", 5);

  tree.eachLeafLabel((label: HTMLElement) => {
    label.style.cursor = "pointer";
    label.onclick = () => openSamplePage(label.innerHTML);
  });
}

function openSamplePage(id: string): void {
  const groupNamePos = window.location.pathname.split("/").indexOf("sample");
  const baseUrl = window.location.pathname
    .split("/")
    .slice(0, groupNamePos)
    .join("/");
  window.open(`${baseUrl}/sample/${id}`);
}

/* update qc status in header section of sample view */
export function updateQcStatus(status: ApiSampleQcStatus): void {
  const header = document.getElementById('sample-header')
  if (!header) return;

  const statusField = header.querySelector("span[name='qc-status']") as HTMLSpanElement;
  const actionContainer = header.querySelector("span[name='container']") as HTMLSpanElement;
  const actionField = header.querySelector("span[name='action']") as HTMLSpanElement;
  const commentField = header.querySelector("span[name='comment']") as HTMLSpanElement;

  if (!statusField || !actionContainer || !actionField || !commentField) {
    console.error('DOM elements used by QC status update function were not found');
    return;
  }

  // Set status text and formatting
  statusField.innerText = status.status ? status.status.charAt(0).toUpperCase() + status.status.slice(1) : '';
  if (status.status === 'passed') {
    statusField.className = 'text-success';
  } else if (status.status === 'failed') {
    statusField.className = 'text-danger';
  } else {
    statusField.className = '';
  }

  // Show/hide action/comment container
  if (status.status === 'failed' && status.action) {
    actionContainer.hidden = false;
    actionField.innerText = status.action ? status.action.charAt(0).toUpperCase() + status.action.slice(1) : '';
    commentField.innerText = status.comment ? status.comment.charAt(0).toUpperCase() + status.comment.slice(1) : '';
  } else {
    actionContainer.hidden = true;
    actionField.innerText = '';
    commentField.innerText = '';
  }
}

