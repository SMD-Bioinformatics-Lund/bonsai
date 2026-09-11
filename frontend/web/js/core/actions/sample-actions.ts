// Description: Functions to handle sample-related operations such as finding similar samples and adding selected samples to a group.

import { ApiService, pollJob, ApiError } from "../api";
import { emitEvent } from "../../utils/event-bus";
import { throwSmallToast } from "../../utils/notification";
import { TableController } from "../../utils/table-controller";
import { ApiFindSimilarInput } from "../types";
import { ApiJobStatusNewick, ApiJobStatusSimilarity, ApiSampleQcStatus } from "../types";
import { ClusterMethod, TypingMethod } from "../types/enums";
import { hideSpinner, showSpinner } from "./spinner-actions";
import SpinnerElement from "../../components/spinner-element";
import "../../components/spinner-element";

type ApiProblemDetails = {
  title?: unknown;
  type?: unknown;
};

type RemoveSamplesFromGroupApi = {
  removeSamplesFromGroup(groupId: string, sampleIds: string[]): Promise<void>;
};

type TidyTreeSelection = {
  selectAll(selector: string): TidyTreeSelection;
  style(name: string, value: string): TidyTreeSelection;
  attr(name: string, value: number): TidyTreeSelection;
};

type TidyTreeInstance = {
  search(predicate: (node: { data: { id: string } }) => boolean): TidyTreeSelection;
  eachLeafLabel(callback: (label: HTMLElement) => void): void;
};

type DendrogramLeaf = {
  element: HTMLElement;
  sampleId: string;
};

type TidyTreeConstructor = new (
  newick: string,
  options: Record<string, unknown>,
) => TidyTreeInstance;

export async function getSimilarSamplesAndCheckRows(
  btn: HTMLButtonElement,
  dt: TableController,
  api: ApiService,
  narrow_search_to: string[] | null,
) {
  const container = btn.closest(".similar-samples-container") as HTMLDivElement;
  const limitInput = container.querySelector("#similar-samples-limit") as HTMLInputElement;
  const similarityInput = container.querySelector("#similar-samples-threshold") as HTMLInputElement;
  showSpinner(container);
  const sampleId = dt.getSelectedRows()[0];
  if (sampleId === undefined || sampleId === "undefined")
    throw Error(`Undefined sampleId; selected rows: ${dt.getSelectedRows()}`);
  const job = await api.findSimilarSamples(sampleId, {
    limit: parseInt(limitInput.value),
    similarity: parseFloat(similarityInput.value),
    narrow_to_sample_ids: narrow_search_to,
    cluster: false,
    typing_method: null,
    cluster_method: null,
  });
  // start polling for job status
  try {
    const jobFunc = async () => api.checkJobStatus(job.id) as Promise<ApiJobStatusSimilarity>;
    const result = await pollJob(jobFunc, 3000);
    dt.selectedRows = result.result.map((sample) => sample.sample_id);
    throwSmallToast(
      `Search complete: ${result.result.length} similar samples identified`,
      "success",
    );
  } catch (error) {
    console.error("Error while checking job status:", error);

    // Parse API error response for user-friendly message
    let message = "Error while finding similar samples. Please try again.";
    if (error instanceof ApiError && error.data) {
      const data = error.data as ApiProblemDetails;
      if (data.title && typeof data.title === "string") {
        message = data.title;
      }
      if (data.type === "urn:bonsai:problem:audit-log-unavailable") {
        message = "Service temporarily unavailable due to logging issues. Please try again later.";
      }
    }

    throwSmallToast(message, "error");
  }
  hideSpinner(container);
}

export function removeSamplesFromGroup(
  groupId: string,
  table: TableController,
  api: RemoveSamplesFromGroupApi,
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
      throwSmallToast(`Removed ${selectedSamples.length} samples from group`, "success");
    })
    .catch((error) => {
      console.error(`Error removing ${selectedSamples.length} from group:`, error);

      // Parse API error response for user-friendly message
      let message = `Failed to remove ${selectedSamples.length} samples from group. Please try again.`;
      if (error instanceof ApiError && error.data) {
        const data = error.data as ApiProblemDetails;
        if (data.title && typeof data.title === "string") {
          message = data.title;
        }
        if (data.type === "urn:bonsai:problem:audit-log-unavailable") {
          message =
            "Service temporarily unavailable due to logging issues. Please try again later.";
        }
      }

      throwSmallToast(message, "error");
    });
}

export function deleteSelectedSamples(table: TableController, api: ApiService): void {
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

      // Parse API error response for user-friendly message
      let message = "Failed to delete samples. Please try again.";
      if (error instanceof ApiError && error.data) {
        const data = error.data as ApiProblemDetails;
        // Use the API's problem-details title if available and safe
        if (data.title && typeof data.title === "string") {
          message = data.title;
        }
        // Optionally map specific types to custom messages
        if (data.type === "urn:bonsai:problem:audit-log-unavailable") {
          message =
            "Service temporarily unavailable due to logging issues. Please try again later.";
        }
      }

      throwSmallToast(message, "error");
    });
}

/* Setup listeners and functionality of set Qc status form */
export function initSetSampleQc(
  getSampleIds: () => string[],
  submitQc: (sampleId: string, data: ApiSampleQcStatus) => Promise<unknown>,
  onStatusChange: (status: ApiSampleQcStatus, sampleIds: string[]) => void,
  form: HTMLElement,
) {
  const passedQcBtn = form.querySelector("#passed-qc-btn") as HTMLButtonElement;
  const failedQcBtn = form.querySelector("#failed-qc-btn") as HTMLButtonElement;
  const failedQcAction = form.querySelector("#failed-qc-action") as HTMLSelectElement;
  const failedQcComment = form.querySelector("#failed-qc-comment-container") as HTMLTextAreaElement;
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
    const qcStatus = form.querySelector("input[name='qc-validation']:checked") as HTMLInputElement;
    submitBtn.disabled = failedQcAction.value === "" && qcStatus.value === "failed";
  };

  // add submit function
  submitBtn.onclick = async (e: Event) => {
    e.preventDefault();
    const sampleIds = getSampleIds();
    if (sampleIds.length === 0) {
      throwSmallToast("No samples selected", "warning");
      return;
    }

    const status = form.querySelector("input[name='qc-validation']:checked") as HTMLInputElement;
    const isFailed: boolean = status.value === "failed";
    const qcStatus: ApiSampleQcStatus = {
      status: status.value,
      action: isFailed ? failedQcAction.value : null,
      comment: isFailed ? failedQcComment.querySelector("textarea").value : "",
    };

    submitBtn.disabled = true;
    const results = await Promise.allSettled(
      sampleIds.map((sampleId) => submitQc(sampleId, qcStatus)),
    );
    submitBtn.disabled = false;

    const updatedSampleIds: string[] = [];
    results.forEach((result, index) => {
      const sampleId = sampleIds[index];
      if (result.status === "fulfilled") {
        updatedSampleIds.push(sampleId);
      } else {
        const error = result.reason;
        console.error(`Error updating QC of sample: ${sampleId}`, error);

        // Parse API error response for user-friendly message
        let message = "Failed to update sample QC. Please try again.";
        if (error instanceof ApiError && error.data) {
          const data = error.data as ApiProblemDetails;
          if (data.title && typeof data.title === "string") {
            message = data.title;
          }
          if (data.type === "urn:bonsai:problem:audit-log-unavailable") {
            message =
              "Service temporarily unavailable due to logging issues. Please try again later.";
          }
        }

        throwSmallToast(message, "error");
      }
    });

    if (updatedSampleIds.length > 0) {
      onStatusChange(qcStatus, updatedSampleIds);
      const sampleLabel = updatedSampleIds.length === 1 ? "sample" : "samples";
      throwSmallToast(`Updated QC of ${updatedSampleIds.length} ${sampleLabel}`, "success");
    }
  };
}

/* Find samples similar to the given sample id, cluster them and plot as dendrogram */
export async function findAndClusterSimilarSamples(
  sampleId: string,
  narrow_to_sample_ids: string[] | null,
  api: ApiService,
): Promise<string | null> {
  let jobResult: ApiJobStatusNewick | undefined;
  const container = document.getElementById("similar-samples-card");
  const spinner = container.querySelector("spinner-element") as SpinnerElement;
  spinner?.show();
  const searchParams: ApiFindSimilarInput = {
    limit: 10,
    similarity: 0.9,
    cluster: true,
    narrow_to_sample_ids: narrow_to_sample_ids,
    typing_method: TypingMethod.MINHASH,
    cluster_method: ClusterMethod.SINGLE,
  };
  // queue similar samples job
  const job = await api.findSimilarSamples(sampleId, searchParams);
  console.log("Waiting for the following job ID:", job.id);
  try {
    const jobFunc = async () => api.checkJobStatus(job.id) as Promise<ApiJobStatusNewick>;
    jobResult = await pollJob(jobFunc, 3000, 40);
    console.log("Here is the find similar result:", jobResult.result);

    // draw dendrogam in container element
    const leaves = drawDendrogram("#tree-body", jobResult.result, sampleId);
    await showLabIds(leaves, api);
  } catch (error) {
    container.hidden = true;

    // Parse API error response for user-friendly message
    let message = "Error while finding similar samples. Please try again.";
    let notificationType = "error";
    if (error instanceof ApiError && error.data) {
      const data = error.data as ApiProblemDetails;
      if (data.title && typeof data.title === "string") {
        message = data.title;
      }
      if (data.type === "urn:bonsai:problem:audit-log-unavailable") {
        message = "Service temporarily unavailable due to logging issues. Please try again later.";
      }
    } else if (error instanceof Error) {
      if (error.message.includes("No record found for sample_id")) {
        message = "Similarity data is not available for this sample.";
        notificationType = "warning";
      } else {
        message = error.message;
      }
    }

    if (notificationType === "error") {
      console.error("Error while checking job status:", error);
    }

    throwSmallToast(message, notificationType);
    return null;
  } finally {
    spinner?.hide();
  }
  if (!jobResult || !jobResult.result) {
    console.error("Job result is missing or malformed:", jobResult);
    throw new Error("Job result is undefined");
  }

  return jobResult.result;
}

/* Draw dendrogram from Newick string */
export function drawDendrogram(
  containerSelector: string,
  newick: string,
  sampleId: string,
): DendrogramLeaf[] {
  const container = document.querySelector(containerSelector);
  if (!container) {
    console.error(`Container element not found: ${containerSelector}`);
    return [];
  }
  const TidyTree = (window as Window & { TidyTree?: TidyTreeConstructor }).TidyTree;
  if (!TidyTree) {
    console.error("TidyTree library is not loaded");
    return [];
  }
  const tree = new TidyTree(newick, {
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

  const leaves: DendrogramLeaf[] = [];
  tree.eachLeafLabel((label: HTMLElement) => {
    const leafSampleId = label.textContent ?? "";
    leaves.push({ element: label, sampleId: leafSampleId });
    label.style.cursor = "pointer";
    label.onclick = () => openSamplePage(leafSampleId);
  });
  return leaves;
}

async function showLabIds(leaves: DendrogramLeaf[], api: ApiService): Promise<void> {
  const sampleIds = leaves.map((leaf) => leaf.sampleId).filter(Boolean);
  if (sampleIds.length === 0) return;

  const response = await api.getSamplesDetails({
    sid: sampleIds,
    fields: ["sample_id", "external_sample_id"],
    limit: sampleIds.length,
    offset: 0,
  });
  const labIds = new Map(
    response.data.map((sample) => [sample.sample_id, sample.external_sample_id]),
  );
  leaves.forEach(({ element, sampleId: internalSampleId }) => {
    element.textContent = labIds.get(internalSampleId) || "Lab ID unavailable";
  });
}

function openSamplePage(id: string): void {
  const groupNamePos = window.location.pathname.split("/").indexOf("sample");
  const baseUrl = window.location.pathname.split("/").slice(0, groupNamePos).join("/");
  window.open(`${baseUrl}/sample/${id}`);
}

/* update qc status in header section of sample view */
export function updateQcStatus(status: ApiSampleQcStatus): void {
  const header = document.getElementById("sample-header");
  if (!header) return;

  const statusField = header.querySelector("span[name='qc-status']") as HTMLSpanElement;
  const actionContainer = header.querySelector("span[name='container']") as HTMLSpanElement;
  const actionField = header.querySelector("span[name='action']") as HTMLSpanElement;
  const commentField = header.querySelector("span[name='comment']") as HTMLSpanElement;

  if (!statusField || !actionContainer || !actionField || !commentField) {
    console.error("DOM elements used by QC status update function were not found");
    return;
  }

  // Set status text and formatting
  statusField.innerText = status.status
    ? status.status.charAt(0).toUpperCase() + status.status.slice(1)
    : "";
  if (status.status === "passed") {
    statusField.className = "text-success";
  } else if (status.status === "failed") {
    statusField.className = "text-danger";
  } else {
    statusField.className = "";
  }

  // Show/hide action/comment container
  if (status.status === "failed" && status.action) {
    actionContainer.hidden = false;
    actionField.innerText = status.action
      ? status.action.charAt(0).toUpperCase() + status.action.slice(1)
      : "";
    commentField.innerText = status.comment
      ? status.comment.charAt(0).toUpperCase() + status.comment.slice(1)
      : "";
  } else {
    actionContainer.hidden = true;
    actionField.innerText = "";
    commentField.innerText = "";
  }
}
