import { ApiError, ApiService, pollJob } from "../api";
import { throwSmallToast } from "../../utils/notification";
import { ApiJobStatusNewick, ApiClusterInput, ApiUncallableSample } from "../types";
import { ClusterMethod, DistanceMethod, TypingMethod } from "../types/enums";
import { hideSpinner, showSpinner } from "./spinner-actions";

type ApiProblemDetails = {
  detail?: unknown;
  type?: string;
  typing_method?: string;
  samples?: ApiUncallableSample[];
};

function getUncallableSamples(
  problem: ApiProblemDetails,
  typingMethod: TypingMethod,
  sampleIds: string[],
): ApiUncallableSample[] | null {
  if (
    problem.type !== "urn:bonsai:problem:no-usable-allele-calls" ||
    (typingMethod !== TypingMethod.MLST && typingMethod !== TypingMethod.CGMLST) ||
    problem.typing_method !== typingMethod ||
    !Array.isArray(problem.samples) || problem.samples.length === 0
  ) return null;

  const validSamples = problem.samples.every((sample) =>
    sample && typeof sample.sample_id === "string" &&
    typeof sample.label === "string" && sampleIds.includes(sample.sample_id),
  );
  return validSamples ? problem.samples : null;
}

async function summarizeMissingClusterData(
  message: string,
  sampleIds: string[],
  api: ApiService,
): Promise<string> {
  // Recognize the existing API/worker messages without changing job payloads.
  const reasons = [
    ["No cgMLST typing profile is available for the following samples: ", "cgMLST typing profiles are unavailable"],
    ["No MLST typing profile is available for the following samples: ", "MLST typing profiles are unavailable"],
    ["No SKA index is available for the following samples: ", "SKA indexes are unavailable"],
    ["No SKA index file is available for the following samples: ", "SKA index files are unavailable"],
    ["Could not load exactly one MinHash signature per selected sample: ", "MinHash signatures are unavailable or invalid"],
  ];
  const detail = message.replace(/^(?:ValueError|FileNotFoundError): /, "");
  const reason = reasons.find(([prefix]) => detail.startsWith(prefix));
  if (!reason) return message;

  const labels = detail.slice(reason[0].length).split(", ").filter(Boolean);
  if (labels.length === 0) return message;
  const summary = `Cannot cluster: ${reason[1]} for ${labels.length} ${labels.length === 1 ? "sample" : "samples"}.`;
  if (labels.length > 4) return summary;

  // Most API errors already contain Lab IDs; MinHash errors contain internal IDs.
  const internalIds = labels.filter((label) => sampleIds.includes(label));
  if (internalIds.length > 0) {
    try {
      const response = await api.getSamplesDetails({
        sid: internalIds,
        fields: ["sample_id", "external_sample_id"],
        limit: internalIds.length,
        offset: 0,
      });
      const labIds = new Map(response.data.map((sample) => [sample.sample_id, sample.external_sample_id?.trim()]));
      if (internalIds.some((id) => !labIds.get(id))) return summary;
      labels.forEach((label, index) => {
        labels[index] = labIds.get(label) || label;
      });
    } catch {
      // A failed label lookup must not hide the original clustering failure.
      return summary;
    }
  }
  return `Cannot cluster: ${reason[1]} for ${labels.join(", ")}.`;
}

async function openGrapeTree(
  newick: string,
  sampleIds: string[],
  clusterMethod: TypingMethod,
): Promise<void> {
  // Open grape tree
  const template = document.createElement("template");
  template.innerHTML = String.raw`
  <form id="open-tree-form" action="${baseUrl}/tree" method="POST" hidden target="_blank">
      <input type="text" name="newick" id="newick-content" value="${newick}">
      <input type="text" name="typing_data" id="typing-data-content" value="${clusterMethod}">
      <input type="text" name="sample-ids" id="sample-ids-content" value='${JSON.stringify({ sample_id: sampleIds })}'>
      <input type="text" name="metadata" id="metadata-content" value="">
      <input type="submit" value="">
  </form>
  `;
  document.body.appendChild(template.content);
  const submitBnt = document.querySelector(
    "#open-tree-form input[type=submit]",
  ) as HTMLInputElement;
  submitBnt.click();
  // clean up
  document.querySelector("#open-tree-form").remove();
}

// cluter all samples in basket
export async function clusterSamples(
  element: HTMLLinkElement,
  sampleIds: string[],
  api: ApiService,
  onUncallableSamples?: (method: TypingMethod, samples: ApiUncallableSample[]) => void,
) {
  const typingMethodEnum = element.getAttribute("data-bi-typing-method") as TypingMethod;
  // base dropdown element
  const baseElement = document.querySelector("#basket-cluster-samples");
  const btn = baseElement.querySelector(".btn") as HTMLButtonElement;
  // construct body to pass
  let body: ApiClusterInput;
  switch (typingMethodEnum) {
    case TypingMethod.CGMLST:
      body = {
        sampleIds: sampleIds,
        distance: DistanceMethod.HAMMING,
        method: ClusterMethod.MSTREE2,
      };
      break;
    case TypingMethod.MLST:
      body = {
        sampleIds: sampleIds,
        distance: DistanceMethod.HAMMING,
        method: ClusterMethod.MSTREE2,
      };
      break;
    case TypingMethod.MINHASH:
      body = {
        sampleIds: sampleIds,
        distance: DistanceMethod.HAMMING,
        method: ClusterMethod.SINGLE,
      };
      break;
    case TypingMethod.SKA:
      body = {
        sampleIds: sampleIds,
        distance: DistanceMethod.HAMMING,
        method: ClusterMethod.SINGLE,
      };
      break;
  }
  showSpinner(btn);
  try {
    // Submit the job and poll for updates.
    const jobInfo = await api.clusterSamples(typingMethodEnum, body);
    throwSmallToast(`Clustering samples: ${sampleIds.length}`, "info");
    const result = (await pollJob(
      () => api.checkJobStatus(jobInfo.id),
      3000,
    )) as ApiJobStatusNewick;

    openGrapeTree(result.result, sampleIds, typingMethodEnum);
  } catch (error) {
    let message = "A problem occurred during clustering";
    if (error instanceof ApiError && error.data) {
      const problem = error.data as ApiProblemDetails;
      const detail = problem.detail;
      if (typeof detail === "string") message = detail;
      const uncallableSamples = getUncallableSamples(problem, typingMethodEnum, sampleIds);
      if (uncallableSamples) {
        onUncallableSamples?.(typingMethodEnum, uncallableSamples);
        const name = typingMethodEnum === TypingMethod.CGMLST ? "cgMLST" : "MLST";
        message = `Cannot cluster by ${name}: ${uncallableSamples.length} ${uncallableSamples.length === 1 ? "sample has" : "samples have"} no usable allele calls. Remove the affected samples from the basket to continue.`;
      }
    } else if (error instanceof Error) {
      message = error.message;
    }

    message = await summarizeMissingClusterData(message, sampleIds, api);

    if (typingMethodEnum === TypingMethod.SKA && message.includes("Duplicate names found")) {
      message = `SNV clustering failed for ${sampleIds.length} selected samples because the server data contains duplicate sequence IDs. Please contact the server administrator.`;
    }

    if (/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i.test(message)) {
      message = "Could not cluster the selected samples. Please contact the server administrator.";
    }

    throwSmallToast(message, "error");
    console.error("A problem occurred during clustering:", {
      typingMethod: typingMethodEnum,
      sampleIds,
      error,
    });
  } finally {
    hideSpinner(btn);
  }
}
