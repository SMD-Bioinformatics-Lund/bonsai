import { ApiGetSamplesDetailsInput, SamplesDetails, ApiSampleDetailsResponse } from "../core/types";
import { BasketState } from "../core/state/basket-state";

export class BasketComponent extends HTMLElement {
  private state: BasketState;
  private renderVersion = 0;
  private ready = false;
  private qcFailedSampleIds = new Set<string>();
  private getSamplesDetails: (
    query: ApiGetSamplesDetailsInput,
  ) => Promise<ApiSampleDetailsResponse>;

  constructor(
    state: BasketState,
    getSamplesDetails: (query: ApiGetSamplesDetailsInput) => Promise<ApiSampleDetailsResponse>,
  ) {
    super();
    this.state = state;
    this.getSamplesDetails = getSamplesDetails;
    this.handleStateChange = this.handleStateChange.bind(this);
  }

  connectedCallback() {
    this.state.onSelection(this.handleStateChange);
    this.render();
  }

  disconnectedCallback() {
    this.state.offSelection(this.handleStateChange);
    this.renderVersion++;
    this.setReady(false);
  }

  get canCluster(): boolean {
    return this.ready && this.state.getSampleIds().length >= 2;
  }

  private setReady(ready: boolean): void {
    this.ready = ready;
    this.dispatchEvent(new CustomEvent("basket:ready-change"));
  }

  private handleStateChange() {
    this.qcFailedSampleIds.clear();
    this.render();
  }

  showQcBlocked(sampleIds: string[]): void {
    const basketIds = new Set(this.state.getSampleIds());
    this.qcFailedSampleIds = new Set(sampleIds.filter((id) => basketIds.has(id)));
    this.render();
  }

  async render() {
    const version = ++this.renderVersion;
    this.setReady(false);
    const sampleIds = this.state.getSampleIds();
    if (sampleIds.length === 0) {
      this.innerHTML = "<p>Your basket is empty.</p>";
      return;
    }
    this.innerHTML = "<p>Loading basket...</p>";
    try {
      const query: ApiGetSamplesDetailsInput = {
        sid: sampleIds,
        prediction_result: true,
        qc: false,
        limit: 0,
        skip: 0,
      };
      const data = await this.getSamplesDetails(query);
      // A newer selection or render owns the basket now.
      if (version !== this.renderVersion) return;
      const samplesById = new Map(data.data.map((sample) => [sample.sample_id, sample]));
      const missingIds = sampleIds.filter((id) => !samplesById.has(id));
      if (missingIds.length > 0) {
        // The state change renders and validates the remaining basket again.
        this.state.removeSamples(missingIds);
        return;
      }
      this.innerHTML = "";
      const failedIds = sampleIds.filter((id) => this.qcFailedSampleIds.has(id));
      if (failedIds.length > 0) {
        const count = failedIds.length;
        const notice = document.createElement("div");
        notice.className = "alert alert-warning py-2";
        notice.setAttribute("role", "status");
        notice.innerHTML = `
          <p class="mb-2">Clustering could not run because ${count} ${count === 1 ? "sample failed QC and is" : "samples failed QC and are"} excluded from MinHash analysis.</p>
          <button type="button" class="btn btn-sm btn-outline-secondary" data-remove-qc-failed>
            Remove ${count} QC-failed ${count === 1 ? "sample" : "samples"} from basket
          </button>
          <p class="small mb-0 mt-2">This changes your basket only. Sample data and QC status are preserved.</p>
        `;
        notice.querySelector("[data-remove-qc-failed]").addEventListener("click", () => {
          this.state.removeSamples(failedIds);
        });
        this.appendChild(notice);
      }
      if (sampleIds.length < 2) {
        const notice = document.createElement("p");
        notice.textContent = "At least two samples are needed for clustering.";
        this.appendChild(notice);
      }
      // create sample cards for each sample in the basket
      sampleIds.forEach((id) => {
        const sample: SamplesDetails = samplesById.get(id);
        const item = document.createElement("div");
        item.className = "card mb-2 rounded-1 p-0 sample_in_basket";
        const qcFailed = this.qcFailedSampleIds.has(id);
        if (qcFailed) item.className += " border-danger bg-danger bg-opacity-10";
        item.innerHTML = String.raw`
        <div class="card-body py-1 d-flex flex-row justify-content-between align-items-center">
            <a class="text-muted d-flex flex-column" href="${baseUrl}/sample/${sample.sample_id}">
                <h6 id="${sample.sample_id}" class="text-uppercase fw-bold text-muted my-0 py-0">${sample.sample_name}</h6>
                <i class="text-muted fs-6 fw-light p-0">${sample.assay}</i>
                ${qcFailed ? '<span class="text-danger small fw-semibold">QC failed — excluded from clustering</span>' : ""}
            </a>
            <button class="float-end float-top btn btn-sm btn-outline-danger" aria-label="Remove" type="button" data-id="${sample.sample_id}">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </div>
        `;
        this.appendChild(item);
      });
      this.querySelectorAll("button[data-id]").forEach((button) => {
        button.addEventListener("click", (e) => {
          const id = (e.currentTarget as HTMLElement).getAttribute("data-id");
          if (id) {
            this.state.removeSamples([id]);
          }
        });
      });
      this.setReady(true);
    } catch (error) {
      if (version !== this.renderVersion) return;
      this.innerHTML = "<p>Could not load your basket. Reopen it to retry.</p>";
      console.error("Failed to render basket:", error);
    }
  }
}

customElements.define("basket-component", BasketComponent);
