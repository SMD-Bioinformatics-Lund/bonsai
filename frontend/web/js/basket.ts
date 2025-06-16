import { ApiService, pollJob } from "./api";
import { throwSmallToast } from "./notification";
import { hideSpinner, showSpinner } from "./util";
import {
  ApiClusterInput,
  ApiGetSamplesDetailsInput,
  ApiJobStatusNewick,
  ApiSampleDetailsResponse,
  SamplesDetails,
} from "./types";
import { ClusterMethod, DistanceMethod, TypingMethod } from "./constants";

export class SampleBasket {
  private name = "basket";
  private sampleIds: Set<string> = new Set();
  private additionListeners: Set<CallableFunction> = new Set();

  constructor(
    private getSamplesDetails: (
      query: ApiGetSamplesDetailsInput,
    ) => Promise<ApiSampleDetailsResponse>,
  ) {
    // load state from local storage
    this.loadState();
  }

  onSelection = (callback: CallableFunction): void => {
    this.additionListeners.add(callback);
  };

  offSelection = (callback: CallableFunction): void => {
    this.additionListeners.delete(callback);
  };

  getSampleIds = (): string[] => {
    return Array.from(this.sampleIds);
  };

  addSamples = (sampleIds: string[]): void => {
    sampleIds.forEach((id) => this.sampleIds.add(id));
    this.saveState();
    this.notifyChange();
  };

  removeSamples = (sampleIds: string[]): void => {
    sampleIds.forEach((id) => this.sampleIds.delete(id));
    this.saveState();
    this.notifyChange();
  };

  clear = (): void => {
    this.sampleIds.clear();
    this.saveState();
    this.notifyChange();
  };

  render = async (): Promise<void> => {
    // render the basket content
    // reset the basket content
    const container = document.querySelector("#basket-content");
    if (!container) return;

    container.innerHTML = "";
    const sampleIds = this.getSampleIds();
    // if no samples in basket, show empty message
    if (sampleIds.length === 0) {
      container.innerHTML = "<p>Your basket is empty.</p>";
      return;
    }

    try {
      // query the API for sample details
      const query: ApiGetSamplesDetailsInput = {
        sid: sampleIds,
        prediction_result: true,
        qc: false,
        limit: 0,
        skip: 0,
      };
      const data = await this.getSamplesDetails(query);

      data.data.forEach((sample: SamplesDetails) => {
        const item = document.createElement("div");
        item.className = "card mb-2 rounded-1 p-0 sample_in_basket";
        item.innerHTML = String.raw`
        <div class="card-body py-1 d-flex flex-row justify-content-between align-items-center">
            <a class="text-muted d-flex flex-column" href="/">
                <h6 id="${sample.sample_id}" class="text-uppercase fw-bold text-muted my-0 py-0">${sample.sample_name}</h6>
                <i class="text-muted fs-6 fw-light p-0">${sample.assay}</i>
            </a>
            <button class="float-end float-top btn btn-sm btn-outline-danger" aria-label="Remove" type="button" data-id="${sample.sample_id}">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </div>
        `;
        container.appendChild(item);
      });

      container.querySelectorAll("button[data-id]").forEach((button) => {
        button.addEventListener("click", (e) => {
          const id = (e.currentTarget as HTMLElement).getAttribute("data-id");
          if (id) {
            this.removeSamples([id]);
            this.render(); // Re-render after removal
          }
        });
      });
    } catch (error) {
      console.error("Failed to render basket:", error);
    }
  };

  private notifyChange = (): void => {
    const selected = this.getSampleIds();
    this.additionListeners.forEach((callback) => callback(selected));
  };

  private saveState = (): void => {
    localStorage.setItem(this.storageKey, JSON.stringify(this.getSampleIds()));
  };

  private loadState = (): void => {
    const state = localStorage.getItem(this.storageKey);
    if (state) {
      try {
        const ids = JSON.parse(state) as string[];
        this.sampleIds = new Set(ids);
      } catch (e) {
        console.error("Failed to parse saved basket state", e);
      }
    }
  };

  private get storageKey(): string {
    return `${this.name}_content`;
  }
}

export class SamplesInBasketCounter {
  private badgeElement: HTMLSpanElement | null;
  private counterElement: HTMLSpanElement | null;

  constructor(private elementId: string = "samples-in-basket-badge") {
    this.badgeElement = document.querySelector(`#${elementId}`);
    this.counterElement =
      this.badgeElement?.querySelector("#samples-in-basket-counter") ?? null;
  }

  get counter(): number {
    const value = this.counterElement?.innerText ?? "0";
    const parsed = parseInt(value, 10);
    return isNaN(parsed) ? 0 : parsed;
  }

  set counter(value: number) {
    if (this.counterElement !== null) {
      this.counterElement.innerHTML = value.toString();
      this.badgeElement.hidden = this.counter == 0;
    } else {
      console.error("No counter on this page!");
    }
  }

  reset(): void {
    this.counter = 0;
  }
}

async function openGrapeTree(
  newick: string,
  sampleIds: string[],
  clusterMethod: TypingMethod,
): Promise<void> {
  // Open grape tree
  const template = document.createElement("template");
  template.innerHTML = String.raw`
  <form id="open-tree-form" action="/tree" method="POST" hidden target="_blank">
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
