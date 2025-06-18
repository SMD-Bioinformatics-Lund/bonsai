// event-bus.ts
const eventBus = new EventTarget();

export function emitEvent(name: string, detail?: any) {
  eventBus.dispatchEvent(new CustomEvent(name, { detail }));
}

export function onEvent(name: string, callback: (e: CustomEvent) => void) {
  eventBus.addEventListener(name, callback as EventListener);
}
