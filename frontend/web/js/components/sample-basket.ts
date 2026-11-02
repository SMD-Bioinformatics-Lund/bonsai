import { ApiGetSamplesDetailsInput, SamplesDetails, ApiSampleDetailsResponse } from "../core/types";
import { BasketState } from "../core/state/basket-state";

export class BasketComponent extends HTMLElement {
  private state: BasketState;
  private renderVersion = 0;
  private reconciling = false;
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
  }

  private handleStateChange() {
    if (!this.reconciling) this.render();
  }

  async render(): Promise<boolean> {
    const version = ++this.renderVersion;
    const sampleIds = this.state.getSampleIds();
    if (sampleIds.length === 0) {
      this.innerHTML = "<p>Your basket is empty.</p>";
      return true;
    }
    this.innerHTML = '<p role="status">Loading basket…</p>';
    try {
      const query: ApiGetSamplesDetailsInput = {
        sid: sampleIds,
        fields: ["sample_id", "sample_name", "assay"],
        limit: 0,
        offset: 0,
      };
      const data = await this.getSamplesDetails(query);
      if (version !== this.renderVersion) return false;
      const requested = new Set(sampleIds);
      if (!Array.isArray(data.data) || data.data.some(sample => !requested.has(sample.sample_id))) {
        throw new Error("Invalid basket response");
      }
      const samples = new Map(data.data.map(sample => [sample.sample_id, sample]));
      const missing = sampleIds.filter(id => !samples.has(id));
      if (missing.length > 0) {
        console.warn("Removing unavailable samples from basket:", missing);
        // Notify the counter and save the corrected selection without starting
        // another fetch from this component's own state-change callback.
        this.reconciling = true;
        try {
          this.state.removeSamples(missing);
        } finally {
          this.reconciling = false;
        }
      }
      this.innerHTML = "";
      if (missing.length > 0) {
        const notice = document.createElement("p");
        notice.textContent = "Unavailable samples were removed from your basket.";
        this.appendChild(notice);
      }
      if (samples.size === 0) {
        const empty = document.createElement("p");
        empty.textContent = "Your basket is empty.";
        this.appendChild(empty);
      }
      // create sample cards for each sample in the basket
      this.state.getSampleIds().forEach(id => {
        const sample: SamplesDetails = samples.get(id);
        const item = document.createElement("div");
        item.className = "card mb-2 rounded-1 p-0 sample_in_basket";
        item.innerHTML = String.raw`
        <div class="card-body py-1 d-flex flex-row justify-content-between align-items-center">
            <a class="text-muted d-flex flex-column">
                <h6 class="text-uppercase fw-bold text-muted my-0 py-0"></h6>
                <i class="text-muted fs-6 fw-light p-0"></i>
            </a>
            <button class="float-end float-top btn btn-sm btn-outline-danger" aria-label="Remove" type="button">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </div>
        `;
        item.querySelector("a").href = `${baseUrl}/sample/${encodeURIComponent(sample.sample_id)}`;
        item.querySelector("h6").textContent = sample.sample_name;
        item.querySelector("i").textContent = sample.assay || "";
        const button = item.querySelector("button");
        button.dataset.id = sample.sample_id;
        button.onclick = () => this.state.removeSamples([sample.sample_id]);
        this.appendChild(item);
      });
      return true;
    } catch (error) {
      if (version !== this.renderVersion) return false;
      console.error("Failed to render basket:", error);
      this.innerHTML = '<p role="alert">Could not load your basket. Your saved selection has been kept.</p><button type="button" class="btn btn-sm btn-outline-secondary">Retry</button>';
      this.querySelector("button").onclick = () => { this.render(); };
      return false;
    }
  }
}

customElements.define("basket-component", BasketComponent);
