import { ApiError, ApiService, pollJob } from "../api";
import { throwSmallToast } from "../../utils/notification";
import { ApiJobStatusNewick, ApiClusterInput, ApiUnplacedSample } from "../types";
import { ClusterMethod, DistanceMethod, TypingMethod } from "../types/enums";
import { hideSpinner, showSpinner } from "./spinner-actions";

type ApiProblemDetails = {
  detail?: unknown;
};

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
  unplacedSamples: ApiUnplacedSample[] = [],
): Promise<void> {
  const form = document.createElement("form");
  form.action = `${baseUrl}/tree`;
  form.method = "POST";
  form.target = "_blank";
  form.hidden = true;
  const unplacedIds = new Set(unplacedSamples.map((sample) => sample.sample_id));
  const fields = {
    newick,
    typing_data: clusterMethod,
    "sample-ids": JSON.stringify({ sample_id: sampleIds.filter((id) => !unplacedIds.has(id)) }),
    metadata: "",
    "unplaced-samples": JSON.stringify(unplacedSamples),
  };
  Object.entries(fields).forEach(([name, value]) => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  });
  document.body.appendChild(form);
  form.submit();
  form.remove();
}

// cluter all samples in basket
export async function clusterSamples(
  element: HTMLLinkElement,
  sampleIds: string[],
  api: ApiService,
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

    await openGrapeTree(result.result, sampleIds, typingMethodEnum, result.unplaced_samples);
  } catch (error) {
    let message = "A problem occurred during clustering";
    if (error instanceof ApiError && error.data) {
      const detail = (error.data as ApiProblemDetails).detail;
      if (typeof detail === "string") message = detail;
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
