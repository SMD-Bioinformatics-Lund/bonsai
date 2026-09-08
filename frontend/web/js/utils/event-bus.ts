// event-bus.ts
const eventBus = new EventTarget();

export function emitEvent<T = unknown>(name: string, detail?: T) {
  eventBus.dispatchEvent(new CustomEvent(name, { detail }));
}

export function onEvent<T = unknown>(name: string, callback: (e: CustomEvent<T>) => void) {
  eventBus.addEventListener(name, callback as EventListener);
}
