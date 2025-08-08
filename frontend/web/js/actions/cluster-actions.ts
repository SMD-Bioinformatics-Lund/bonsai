import { ApiService, pollJob } from "../api";
import { throwSmallToast } from "../utils/notification";
import { ApiJobStatusNewick, ApiClusterInput } from "../types";
import { ClusterMethod, DistanceMethod, TypingMethod } from "../constants";
import { hideSpinner, showSpinner } from "./spinner-actions";

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
) {
  const typingMethodEnum = element.getAttribute(
    "data-bi-typing-method",
  ) as TypingMethod;
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
  // submit job to API
  showSpinner(btn);
  const jobInfo = await api.clusterSamples(typingMethodEnum, body);
  throwSmallToast(`Clustering samples: ${sampleIds.length}`, "info");
  // start polling for updates
  try {
    const result = (await pollJob(
      () => api.checkJobStatus(jobInfo.id),
      3000,
    )) as ApiJobStatusNewick;
    hideSpinner(btn);
    // open dendrogram
    openGrapeTree(result.result, sampleIds, typingMethodEnum);
  } catch (error) {
    throwSmallToast("A problem occured during clustering", "error");
    hideSpinner(btn);
    console.log(`A problem occured during clustering, ${error}`);
  }
}
