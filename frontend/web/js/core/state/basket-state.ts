export class BasketState {
  private sampleIds: Set<string> = new Set();
  private onChangeCallbacks: Set<(ids: string[]) => void> = new Set();

  constructor(private apiUrl: string, private username: string) {
    this.loadState();
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
    sampleIds.forEach((id) => this.sampleIds.add(id));
    this.saveState();
    this.notifyChange();
  }

  removeSamples(sampleIds: string[]): void {
    let changed = false;
    sampleIds.forEach((id) => {
      if (this.sampleIds.delete(id)) changed = true;
    });
    if (!changed) return;
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
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.getSampleIds()));
    } catch (error) {
      console.error("Failed to save basket state", error);
    }
  }

  private loadState(): void {
    try {
      const state = localStorage.getItem(this.storageKey);
      if (state) {
        const ids: unknown = JSON.parse(state);
        if (!Array.isArray(ids)) throw new Error("Saved basket must be an array");
        this.sampleIds = new Set(ids.filter((id): id is string =>
          typeof id === "string" && id.trim().length > 0,
        ));
      }
    } catch (error) {
      console.error("Failed to load saved basket state", error);
    }
  }

  private get storageKey(): string {
    // The legacy basket_content key has no owner and cannot be safely adopted.
    return `basket_content:${JSON.stringify([this.apiUrl, this.username])}`;
  }
}
