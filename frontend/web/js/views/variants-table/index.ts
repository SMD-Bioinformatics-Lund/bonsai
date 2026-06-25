import { initVariantsView } from "./variants-view";

// expose ONE global entrypoint for Flask
(window as any).initVariantsView = initVariantsView;
