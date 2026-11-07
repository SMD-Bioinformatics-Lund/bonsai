export class BasketState {
  private name = "basket";
  private sampleIds: Set<string> = new Set();
  private onChangeCallbacks: Set<(ids: string[]) => void> = new Set();

  constructor(private readonly userId = document.body?.dataset.bonsaiUser || "anonymous") {
    localStorage.removeItem("basket_content");
    this.loadState();
    window.addEventListener("storage", (event) => {
      if (event.key === this.storageKey || event.key === null) {
        this.loadState();
        this.notifyChange();
      }
    });
  }

  onSelection(callback: (ids: string[]) => void): void {
    this.onChangeCallbacks.add(callback);
  }

  offSelection(callback: (ids: string[]) => void): void {
    this.onChangeCallbacks.delete(callback);
  }

  getSampleIds(): string[] {
    return Array.from(this.sampleIds);
  }

  addSamples(sampleIds: string[]): void {
    this.loadState();
    sampleIds.forEach((id) => this.sampleIds.add(id));
    this.saveState();
    this.notifyChange();
  }

  removeSamples(sampleIds: string[]): void {
    this.loadState();
    sampleIds.forEach((id) => this.sampleIds.delete(id));
    this.saveState();
    this.notifyChange();
  }

  clear(): void {
    this.sampleIds.clear();
    this.saveState();
    this.notifyChange();
  }

  private notifyChange(): void {
    const selected = this.getSampleIds();
    this.onChangeCallbacks.forEach((callback) => callback(selected));
  }

  private saveState(): void {
    localStorage.setItem(this.storageKey, JSON.stringify(this.getSampleIds()));
  }

  private loadState(): void {
    this.sampleIds.clear();
    const state = localStorage.getItem(this.storageKey);
    if (state) {
      try {
        const ids = JSON.parse(state) as string[];
        this.sampleIds = new Set(ids);
      } catch (e) {
        console.error("Failed to parse saved basket state", e);
      }
    }
  }

  private get storageKey(): string {
    return `${this.name}_content:${this.userId}`;
  }
}
