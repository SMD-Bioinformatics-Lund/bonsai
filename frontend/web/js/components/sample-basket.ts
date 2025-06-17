import { ApiGetSamplesDetailsInput, SamplesDetails, ApiSampleDetailsResponse } from "../types";
import { BasketState } from "../state/basket";

export class BasketComponent extends HTMLElement {
  private state: BasketState;
  private getSamplesDetails: (query: ApiGetSamplesDetailsInput) => Promise<ApiSampleDetailsResponse>;

  constructor(state: BasketState, getSamplesDetails: (query: ApiGetSamplesDetailsInput) => Promise<ApiSampleDetailsResponse>) {
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
  }

  private handleStateChange() {
    this.render();
  };

  async render() {
    this.innerHTML = "";
    const sampleIds = this.state.getSampleIds();
    if (sampleIds.length === 0) {
      this.innerHTML = "<p>Your basket is empty.</p>";
      return;
    }
    try {
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
        this.appendChild(item);
      });
      this.querySelectorAll("button[data-id]").forEach((button) => {
        button.addEventListener("click", (e) => {
          const id = (e.currentTarget as HTMLElement).getAttribute("data-id");
          if (id) {
            this.state.removeSamples([id]);
            // Remove the DOM element for the removed sample
            const card = (e.currentTarget as HTMLElement).closest(".sample_in_basket");
            if (card) card.remove();
          }
        });
      });
    } catch (error) {
      console.error("Failed to render basket:", error);
    }
  }
}

customElements.define("basket-component", BasketComponent);