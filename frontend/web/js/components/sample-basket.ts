import { ApiGetSamplesDetailsInput, SamplesDetails, ApiSampleDetailsResponse, ApiUncallableSample } from "../core/types";
import { BasketState } from "../core/state/basket-state";
import { TypingMethod } from "../core/types/enums";

export class BasketComponent extends HTMLElement {
  private state: BasketState;
  private renderVersion = 0;
  private ready = false;
  private qcFailedSampleIds = new Set<string>();
  private uncallableSampleIds = new Set<string>();
  private getSamplesDetails: (
    query: ApiGetSamplesDetailsInput,
  ) => Promise<ApiSampleDetailsResponse>;

  constructor(
    state: BasketState,
    getSamplesDetails: (query: ApiGetSamplesDetailsInput) => Promise<ApiSampleDetailsResponse>,
    private qcControls?: { feedback: HTMLElement | null; removeButton: HTMLButtonElement | null },
    private alleleControls?: { feedback: HTMLElement | null; removeButton: HTMLButtonElement | null },
  ) {
    super();
    this.state = state;
    this.getSamplesDetails = getSamplesDetails;
    this.handleStateChange = this.handleStateChange.bind(this);
  }

  connectedCallback() {
    this.state.onSelection(this.handleStateChange);
    if (this.qcControls?.removeButton) {
      this.qcControls.removeButton.onclick = () => {
        if (this.ready) this.state.removeSamples([...this.qcFailedSampleIds]);
      };
    }
    if (this.alleleControls?.removeButton) {
      this.alleleControls.removeButton.onclick = () => {
        if (this.ready) this.state.removeSamples([...this.uncallableSampleIds]);
      };
    }
    this.render();
  }

  disconnectedCallback() {
    this.state.offSelection(this.handleStateChange);
    this.renderVersion++;
    this.setReady(false);
    if (this.qcControls?.removeButton) this.qcControls.removeButton.onclick = null;
    if (this.alleleControls?.removeButton) this.alleleControls.removeButton.onclick = null;
    this.clearAlleleFeedback();
  }

  uncallableSamplesHandler(): (method: TypingMethod, samples: ApiUncallableSample[]) => void {
    const version = this.renderVersion;
    return (method, samples) => {
      // A response for a previous selection must not offer removal from this one.
      if (version !== this.renderVersion || !this.ready) return;
      if (!this.alleleControls?.feedback || !this.alleleControls?.removeButton) return;
      const currentIds = new Set(this.state.getSampleIds());
      const affected = samples.filter((sample) => currentIds.has(sample.sample_id));
      if (affected.length === 0) return;
      this.uncallableSampleIds = new Set(affected.map((sample) => sample.sample_id));
      const name = method === TypingMethod.CGMLST ? "cgMLST" : "MLST";
      const count = this.uncallableSampleIds.size;
      const { feedback, removeButton } = this.alleleControls;
      feedback.textContent = `${count} ${count === 1 ? "sample has" : "samples have"} no usable ${name} calls: ${affected.map((sample) => sample.label).join(", ")}. Remove these samples from the basket to continue ${name} clustering.`;
      feedback.hidden = false;
      removeButton.textContent = `Remove ${count} ${count === 1 ? "sample" : "samples"} from basket`;
      removeButton.hidden = false;
    };
  }

  private clearAlleleFeedback(): void {
    this.uncallableSampleIds.clear();
    if (this.alleleControls?.feedback) {
      this.alleleControls.feedback.hidden = true;
      this.alleleControls.feedback.textContent = "";
    }
    if (this.alleleControls?.removeButton) this.alleleControls.removeButton.hidden = true;
  }

  get canCluster(): boolean {
    return this.ready && this.state.getSampleIds().length >= 2;
  }

  private setReady(ready: boolean): void {
    this.ready = ready;
    this.updateQcControls();
    this.dispatchEvent(new CustomEvent("basket:ready-change"));
  }

  private updateQcControls(): void {
    if (!this.qcControls?.feedback || !this.qcControls?.removeButton) return;
    const { feedback, removeButton } = this.qcControls;
    const count = this.qcFailedSampleIds.size;
    const visible = this.ready && count > 0;
    feedback.hidden = !visible;
    removeButton.hidden = !visible;
    removeButton.disabled = !visible;
    feedback.innerHTML = "";
    if (!visible) return;
    feedback.innerHTML = `
      <p class="small text-danger mb-2">${count} ${count === 1 ? "sample is" : "samples are"} marked as QC failed. You can still include them in clustering.</p>
    `;
  }

  private handleStateChange() {
    this.qcFailedSampleIds.clear();
    this.render();
  }

  async render() {
    const version = ++this.renderVersion;
    this.clearAlleleFeedback();
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
        // Fetch curated QC with the card data, before enabling clustering.
        fields: ["sample_id", "sample_name", "assay", "qc_status"],
        limit: 0,
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
      this.qcFailedSampleIds = new Set(
        sampleIds.filter((id) => samplesById.get(id).qc_status?.status === "failed"),
      );
      this.innerHTML = "";
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
        const textColor = qcFailed ? "text-danger" : "text-muted";
        if (qcFailed) {
          item.className += " border-danger bg-danger bg-opacity-10";
          item.setAttribute("role", "group");
          item.setAttribute("aria-label", `${sample.sample_name}: QC failed`);
        }
        item.innerHTML = String.raw`
        <div class="card-body py-1 d-flex flex-row justify-content-between align-items-center">
            <a class="${textColor} d-flex flex-column" href="${baseUrl}/sample/${sample.sample_id}">
                <h6 id="${sample.sample_id}" class="text-uppercase fw-bold ${textColor} my-0 py-0">${sample.sample_name}</h6>
                <i class="${textColor} fs-6 fw-light p-0">${sample.assay}</i>
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
