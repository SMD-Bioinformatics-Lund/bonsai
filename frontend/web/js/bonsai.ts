import * as bootstrap from "bootstrap";
import jQuery from "jquery";

import { initToast, initTooltip, throwSmallToast } from "./utils/notification";
import { ApiService, AuthService, HttpClient } from "./api";
import { initSamplesTable } from "./utils/table-controller";
import {
  deleteSelectedSamples,
  findAndClusterSimilarSamples,
  getSimilarSamplesAndCheckRows,
  initSetSampleQc,
  removeSamplesFromGroup,
  updateQcStatus,
} from "./actions/sample-actions";
import { clusterSamples } from "./actions/cluster-actions";
import { GroupList } from "./components/group-list";
import { GroupSelector } from "./components/group-selector";
import { User } from "./user";
import { BasketState } from "./state/basket-state";
import { SampleBasketCounter } from "./components/samples-basket-counter";
import { BasketComponent } from "./components/sample-basket";

import "./components/group-list";
import "./components/group-selector";
import "./components/spinner-element";


const sampleTableConfig = {
  select: true,
  layout: {
    top1Start: {
      buttons: ["selectAll", "selectNone", "excel"],
    },
    top2Start: "searchBuilder",
  },
  lengthMenu: [10, 25, 50, 100, { label: 'All', value: -1 }],
  scrollX: true,
  pageLength: 50,
};
/* Initialize sample basket */
function initBasket(api: ApiService): BasketState | void {
  const basketElement = document.querySelector("#basket-content") as HTMLElement;
  const counterElement = document.querySelector("#basket-counter-container") as HTMLElement;
  if (!basketElement && !counterElement) {
    console.error('No DOM element for the basket found!');
    return;
  }

  const basketState = new BasketState();
  // init number of samples in basket counter
  const basketCounter = new SampleBasketCounter();
  basketCounter.basketState = basketState;
  counterElement.appendChild(basketCounter);

  // init component for samples in basket
  const basketComponent = new BasketComponent(basketState, api.getSamplesDetails.bind(api));
  basketElement.appendChild(basketComponent);

  // assign functions to DOM objects
  const clusterBtns = document.querySelectorAll(
    "#basket-cluster-samples a",
  ) as NodeListOf<HTMLLinkElement>;
  clusterBtns.forEach((element) => {
    element.onclick = () => clusterSamples(element, basketState.getSampleIds(), api);
  });

  const clearBasketBtn = document.getElementById(
    "clear-basket-btn",
  ) as HTMLButtonElement;
  if (clearBasketBtn) {
    clearBasketBtn.onclick = () => {
      basketState.clear();
    };
  }

  // setup listeners for rendering sample basket when opening it
  const offcanvas = document.getElementById("basket-offcanvas");
  if (offcanvas) {
    offcanvas.addEventListener("show.bs.offcanvas", () => {
      basketComponent.render(); // Assuming you have an instance named sampleBasket
    });
  }
  return basketState;
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
): Promise<void> {
  // setup base functionality
  const api = initApi(bonsaiApiUrl, accessToken, refreshToken);
  const basket = initBasket(api);
  if (!basket) {
    console.error("Something went wrong when initialize the basket")
    return
  }
  const headers = document.querySelectorAll<HTMLTableCellElement>(
    "#sample-table thead td",
  );
  const tableConfig = { ...sampleTableConfig };
  headers.forEach((cell, idx) => {
    if (cell.textContent?.trim() === "Date") {
      tableConfig["order"] = [[idx, "desc"]];
    }
  });
  const table = initSamplesTable("sample-table", tableConfig);
  // get logged in user
  const userInfo = await api.getUserInfo();
  const user = new User(userInfo);
  initToast();
  initTooltip();

  // render groups component
  const groupList = document.createElement("group-list") as GroupList;
  groupList.getGroupInfo = api.getGroups;
  groupList.isAdmin = user.isAdmin;

  const groupContainer = document.getElementById(
    "group-container",
  ) as HTMLElement;
  if (groupContainer) groupContainer.appendChild(groupList);

  // attach function to DOM element
  const addToBasketBtn = document.getElementById(
    "add-to-basket-btn",
  ) as HTMLButtonElement;
  if (addToBasketBtn)
    addToBasketBtn.onclick = () => basket.addSamples(table.getSelectedRows());

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

  // setup add samples to group component
  const groupSelectorContainer = document.getElementById(
    "add-samples-to-group-container",
  ) as HTMLElement;
  if (groupSelectorContainer) {
    const addToGroupSelector = document.createElement(
      "group-selector",
    ) as GroupSelector;
    addToGroupSelector.getGroupInfo = api.getGroups;
    addToGroupSelector.getSelectedSamples = table.getSelectedRows.bind(table);
    addToGroupSelector.AddToGroupFunc = api.addSamplesToGroup.bind(api);
    groupSelectorContainer.appendChild(addToGroupSelector);
  }

  // setup qc classification
  const qcStatusForm = document.getElementById(
    "qc-form-control",
  ) as HTMLButtonElement;
  if (qcStatusForm)
    initSetSampleQc(
      table.getSelectedRows.bind(table),
      api.setSampleQc.bind(api),
      () => console.log('table needs to be redrawn'),
      qcStatusForm,
    );
    // FIXME updating individual cells did not work for some reason
    // the entire table might need to be redrawn.

  const removeFromGroupBtn = document.getElementById(
    "remove-from-group-btn",
  ) as HTMLButtonElement;
  if (removeFromGroupBtn)
    removeFromGroupBtn.onclick = () => {
      const groupId: string =
        removeFromGroupBtn.getAttribute("data-bi-group-id");
      removeSamplesFromGroup(groupId, table, api);
    };
}

/* Initialize interactive elements for the sample view. */
export async function initSampleView(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
  sampleId: string,
): Promise<string> {
  // setup base functionality
  const api = initApi(bonsaiApiUrl, accessToken, refreshToken);
  initToast();

  const qcStatusForm = document.getElementById(
    "qc-classification-form",
  ) as HTMLButtonElement;
  if (qcStatusForm) {
    initSetSampleQc(
      () => [sampleId], 
      api.setSampleQc.bind(api), 
      updateQcStatus,
      qcStatusForm
    );
  }

  await findAndClusterSimilarSamples(sampleId, api);
}

declare global {
  interface Window {
    throwSmallToast: (message: string) => void;
    jQuery: typeof jQuery;
    $: typeof jQuery;
    bootstrap: typeof bootstrap;
  }
  interface HTMLElementTagNameMap {
    "groups-list": GroupList;
  }
}

window.throwSmallToast = throwSmallToast;
window.jQuery = jQuery;
window.$ = jQuery;
window.bootstrap = bootstrap;
