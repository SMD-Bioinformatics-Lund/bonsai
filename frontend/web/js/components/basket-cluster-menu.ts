import { ApiService } from "../core/api";
import { clusterSamples } from "../core/actions/cluster-actions";
import { BasketState } from "../core/state/basket-state";
import { TypingMethod } from "../core/types/enums";

/** Keep clustering choices in sync with the entire basket selection. */
export class BasketClusterMenu {
  private controller?: AbortController;
  private revision = 0;
  private available = new Set<TypingMethod>();
  private links: HTMLAnchorElement[];
  private button: HTMLButtonElement;
  private message: HTMLElement;
  private running = false;

  constructor(
    private element: HTMLElement,
    private state: BasketState,
    private api: ApiService,
  ) {
    this.links = Array.from(element.querySelectorAll<HTMLAnchorElement>("a[data-bi-typing-method]"));
    this.button = element.querySelector<HTMLButtonElement>("button");
    this.message = element.querySelector<HTMLElement>("[data-cluster-status]");
    this.links.forEach((link) => {
      link.onclick = async (event) => {
        event.preventDefault();
        const method = link.dataset.biTypingMethod as TypingMethod;
        if (this.running || !this.available.has(method)) return;
        this.running = true;
        this.button.disabled = true;
        try {
          await clusterSamples(link, this.state.getSampleIds(), this.api);
        } finally {
          this.running = false;
          this.button.disabled = this.available.size === 0;
        }
      };
    });
    this.state.onSelection(() => void this.refresh());
    void this.refresh();
  }

  async refresh(): Promise<void> {
    this.controller?.abort();
    const revision = ++this.revision;
    const ids = this.state.getSampleIds();
    this.available.clear();
    this.update("Checking available clustering methods…");
    if (ids.length < 2) {
      this.update("Add at least two samples to cluster.");
      return;
    }
    this.controller = new AbortController();
    try {
      const result = await this.api.getClusterMethods(ids, this.controller.signal);
      if (revision !== this.revision) return;
      this.available = new Set(result.methods);
      this.update("No clustering method is available for all basket samples.");
    } catch (error) {
      if (revision !== this.revision) return;
      this.update("Unable to check clustering methods. Reopen the basket to retry.");
      console.error("Failed to load clustering methods:", error);
    }
  }

  private update(message: string): void {
    this.links.forEach((link) => {
      const available = this.available.has(link.dataset.biTypingMethod as TypingMethod);
      link.closest("li").hidden = !available;
    });
    this.button.disabled = this.running || this.available.size === 0;
    this.message.textContent = message;
    this.message.hidden = this.available.size > 0;
  }
}
