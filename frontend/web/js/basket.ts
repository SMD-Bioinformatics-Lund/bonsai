import { throwSmallToast } from "./notification";

export class SampleBasket {
  private name = 'basket';
  private sampleIds: Set<string> = new Set();
  private additionListeners: Set<CallableFunction> = new Set();

  constructor(
    private getSamplesDetails: (query: ApiGetSamplesDetailsInput) => Promise<ApiSampleDetailsResponse>
  ) {
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
    sampleIds.forEach(id => this.sampleIds.add(id));
    this.saveState();
    this.notifyChange();
  };

  removeSamples = (sampleIds: string[]): void => {
    sampleIds.forEach(id => this.sampleIds.delete(id));
    this.saveState();
    this.notifyChange();
  };

  clear = (): void => {
    this.sampleIds.clear();
    this.saveState();
    this.notifyChange();
  };

  render = async (): Promise<void> => {
    const query: ApiGetSamplesDetailsInput = {
      sid: this.getSampleIds(),
      prediction_result: true,
      qc: false,
      limit: 0,
      skip: 0,
    };

    try {
      const data = await this.getSamplesDetails(query);
      const container = document.querySelector('#basket-content');
      if (!container) return;

      container.innerHTML = '';

      if (!data || data.data.length === 0) {
        container.innerHTML = '<p>Your basket is empty.</p>';
        return;
      }

      data.data.forEach((sample: SamplesDetails) => {
        const item = document.createElement('div');
        item.className = 'card mb-2 rounded-1 p-0 sample_in_basket';
        item.innerHTML = String.raw`
        <div class="card-body py-1 d-flex flex-row justify-content-between align-items-center">
            <a class="text-muted d-flex flex-column" href="/">
                <h6 id="${sample.sample_id}" class="text-uppercase fw-bold text-muted my-0 py-0">${sample.sample_name}</h6>
                <i class="text-muted fs-6 fw-light p-0">${sample.assay}</i>
            </a>
            <button class="float-end float-top btn btn-sm btn-outline-danger remove-sample-btn" aria-label="Remove" type="button">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </div>
        `;
        const btn = item.querySelector('.remove-sample-btn') as HTMLButtonElement
        btn.onclick = () => this.removeSamples([sample.sample_id])
        container.appendChild(item);
      });

      container.querySelectorAll('button[data-id]').forEach(button => {
        button.addEventListener('click', (e) => {
          const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
          if (id) {
            this.removeSamples([id]);
            this.render(); // Re-render after removal
          }
        });
      });

    } catch (error) {
      console.error('Failed to render basket:', error);
    }
  };

  private notifyChange = (): void => {
    const selected = this.getSampleIds();
    this.additionListeners.forEach(callback => callback(selected));
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
  private badgeElement: HTMLSpanElement | null
  private counterElement: HTMLSpanElement | null

  constructor( private elementId: string = 'samples-in-basket-badge') {
    this.badgeElement = document.querySelector(`#${elementId}`)
    this.counterElement = this.badgeElement?.querySelector('#samples-in-basket-counter') ?? null;
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
      console.error('No counter on this page!')
    }
  }

  reset(): void {
    this.counter = 0
  }
}

export function removeAllSamplesFromBasket(apiUrl: string): void {
  /* remove all samples from the basket and update counter by making a request to front-end api. */
  const body = {
    remove_all: true,
  };
  fetch(`${apiUrl}/api/basket/remove`, {
    method: "POST",
    body: JSON.stringify(body),
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    credentials: "same-origin",
  }).then((response) => {
    if (response.ok) {
      // clear samples from basket
      document.querySelectorAll(".sample_in_basket").forEach((e) => e.remove());
      const counterBadge = document.querySelector("#samples-in-basket-badge") as HTMLSpanElement;
      const counter = counterBadge.querySelector("#samples-in-basket-counter") as HTMLSpanElement;
      counter.innerText = "0";
      counterBadge.hidden = true;
    } else {
      // throw error
      throwSmallToast("Error when removing samples.", "warning");
    }
  });
};