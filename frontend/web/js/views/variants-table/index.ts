import { initVariantsView } from "./variants-view";

// expose ONE global entrypoint for Flask
Object.assign(window, { initVariantsView });
