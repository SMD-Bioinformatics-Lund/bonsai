import { throwSmallToast } from "./notification";
import { TableStateManager } from "./state";

export class basketStateManager {
  private name: string
  private sampleIds: Set<string>
  private additionListeners: Set<TblStateCallbackFunc>;

  constructor() {
    this.name = 'basket';
    this.sampleIds = new Set<string>;
    this.additionListeners = new Set();
  }

  addSample(sampleId: string): void {
    if (!this.sampleIds.has(sampleId)) {
      this.sampleIds.add(sampleId);
      this.saveState();
      this.notifyChange();
    } 
  }

  removeSample(sampleId: string): void {
    if (this.sampleIds.has(sampleId)) {
      this.sampleIds.delete(sampleId);
      this.saveState();
      this.notifyChange();
    } 
  }

  onSelection(callback: TblStateCallbackFunc): void {
    this.additionListeners.add(callback);
  }

  offSelection(callback: TblStateCallbackFunc): void {
    this.additionListeners.delete(callback);
  }

  getSampleIds(): string[] {
    return Array.from(this.sampleIds);
  }

  setSampleIds(ids: string[]): void {
    this.sampleIds = new Set(ids);
    this.saveState();
    this.notifyChange();
  }

  private notifyChange(): void {
    const selected = this.getSampleIds()
    for (const callback of this.additionListeners) {
      callback(selected);
    }
  }

  private saveState(): void {
    localStorage.setItem(this.storageKey, JSON.stringify(this.getSampleIds()));
  }

  private loadState(): void {
    const state = localStorage.getItem(this.storageKey);
    if (state) {
      try {
        const ids = JSON.parse(state) as string[];
        this.sampleIds = new Set(ids);
      } catch (e) {
        console.error("Failed to parse saved table state", e);
      }
    }
  }

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
      this.counterElement.innerHTML = value.toString()
    } else {
      console.error('No counter on this page!')
    }
  }

  add(amount: number): void {
    this.counter = this.counter + amount
  }

  deduct(amount: number): void {
    this.counter = this.counter - amount
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