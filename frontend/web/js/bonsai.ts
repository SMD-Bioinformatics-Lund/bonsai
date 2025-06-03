import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { initToast, throwSmallToast } from "./notification";
import { ApiService, AuthService, HttpClient } from "./api";
import { initSamplesTable } from "./table";
import { clusterSamples, SampleBasket, SamplesInBasketCounter } from "./basket";
import {
  addSelectedSamplesToGroup,
  deleteSelectedSamples,
  getSimilarSamplesAndCheckRows,
} from "./sample";
import { GroupsComponent } from "./components/groups";
import "./components/groups";
import { User } from "./user";

const sampleTableCongig = {
  select: true,
  layout: {
    top1Start: {
      buttons: ["selectAll", "selectNone", "excel"],
    },
    top2Start: "searchBuilder",
  },
};

/* Initialize sample basket */
function initBasket(api: ApiService): SampleBasket {
  const basket = new SampleBasket(api.getSamplesDetails);
  const basketCounter = new SamplesInBasketCounter();
  basketCounter.counter = basket.getSampleIds.length;
  // register callback functions
  basket.onSelection((sampleIds: string[]) => {
    basketCounter.counter = sampleIds.length;
  });

  // assign functions to DOM objects
  const clusterBtns = document.querySelectorAll(
    "#basket-cluster-btn a",
  ) as NodeListOf<HTMLLinkElement>;
  clusterBtns.forEach((element) => {
    element.onclick = () => clusterSamples(element, basket.getSampleIds(), api);
  });
  const clearBasketBtn = document.getElementById(
    "clear-basket-btn",
  ) as HTMLButtonElement;
  if (clearBasketBtn) {
    clearBasketBtn.onclick = () => {
      basket.clear();
      basket.render();
    };
  }

  // setup listeners for rendering sample basket when opening it
  const offcanvas = document.getElementById("basket-offcanvas");
  if (offcanvas) {
    offcanvas.addEventListener("show.bs.offcanvas", () => {
      basket.render(); // Assuming you have an instance named sampleBasket
    });
  }
  return basket;
}

function initApi(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
) {
  const auth = new AuthService(bonsaiApiUrl);
  auth.setTokens(accessToken, refreshToken);
  const http = new HttpClient(bonsaiApiUrl, auth);
  const api = new ApiService(http);
  return api;
}

/* Initialize interactive elements for the group view. */
export async function initGroupView(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
) {
  // setup base functionality
  const api = initApi(bonsaiApiUrl, accessToken, refreshToken);
  const basket = initBasket(api);
  const table = initSamplesTable("sample-table", sampleTableCongig);
  // get logged in user
  const userInfo = await api.getUserInfo();
  const user = new User(userInfo);
  initToast();

  // attach function to DOM element
  const addToBasketBtn = document.getElementById(
    "add-to-basket-btn",
  ) as HTMLButtonElement;
  if (addToBasketBtn)
    addToBasketBtn.onclick = () => basket.addSamples(table.selectedRows);

  const deleteSamplesBtn = document.getElementById(
    "remove-samples-btn",
  ) as HTMLButtonElement;
  if (deleteSamplesBtn)
    deleteSamplesBtn.onclick = () => deleteSelectedSamples(table, api);

  const selectSimilarSamplesBtn = document.getElementById(
    "select-similar-samples-btn",
  ) as HTMLButtonElement;
  if (selectSimilarSamplesBtn)
    selectSimilarSamplesBtn.onclick = () =>
      getSimilarSamplesAndCheckRows(selectSimilarSamplesBtn, table, api);

  const addToGroupBtns = document.querySelectorAll(
    "#add-to-group-btn a",
  ) as NodeListOf<HTMLLinkElement>;
  addToGroupBtns.forEach((element) => {
    element.onclick = () =>
      addSelectedSamplesToGroup(element, table.selectedRows, api);
  });
}

declare global {
  interface Window {
    throwSmallToast: (message: string) => void;
    jQuery: typeof jQuery;
    $: typeof jQuery;
    bootstrap: typeof bootstrap;
  }
  interface HTMLElementTagNameMap {
    "groups-component": GroupsComponent;
  }
}

window.throwSmallToast = throwSmallToast;
window.jQuery = jQuery;
window.$ = jQuery;
window.bootstrap = bootstrap;
