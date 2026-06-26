import { initToast, initTooltip, throwSmallToast } from "../../utils/notification";
import { initSamplesTable } from "../../utils/table-controller";
import {
  deleteSelectedSamples,
  getSimilarSamplesAndCheckRows,
  initSetSampleQc,
  removeSamplesFromGroup,
  updateQcStatus,
} from "../../core/actions/sample-actions";
import { clusterSamples } from "../../core/actions/cluster-actions";
import { GroupList } from "../../components/group-list";
import { GroupSelector } from "../../components/group-selector";
import { User } from "../../core/models/User";
import { BasketState } from "../../core/state/basket-state";
import { SampleBasketCounter } from "../../components/samples-basket-counter";
import { BasketComponent } from "../../components/sample-basket";
import { createGroupViewApi, GroupViewApi } from "./api";

import "../../components/group-list";
import "../../components/group-selector";
import "../../components/spinner-element";
import "../../utils/choice-select";

const sampleTableConfig = {
  select: true,
  layout: {
    top1Start: {
      buttons: ["selectAll", "selectNone", "showSelected"],
    },
    top1End: {
      buttons: ["copy", "csv", "excel"],
    },
    top2Start: "searchBuilder",
  },
  lengthMenu: [10, 25, 50, 100, { label: "All", value: -1 }],
  scrollX: true,
  pageLength: 50,
};

function initBasket(api: GroupViewApi): BasketState | void {
  const basketElement = document.querySelector("#basket-content") as HTMLElement;
  const counterElement = document.querySelector("#basket-counter-container") as HTMLElement;
  if (!basketElement && !counterElement) {
    console.error("No DOM element for the basket found!");
    return;
  }

  const basketState = new BasketState();
  const basketCounter = new SampleBasketCounter();
  basketCounter.basketState = basketState;
  counterElement.appendChild(basketCounter);

  const basketComponent = new BasketComponent(basketState, api.getSamplesDetails.bind(api));
  basketElement.appendChild(basketComponent);

  const clusterBtns = document.querySelectorAll("#basket-cluster-samples a") as NodeListOf<HTMLLinkElement>;
  clusterBtns.forEach((element) => {
    element.onclick = () => clusterSamples(element, basketState.getSampleIds(), api);
  });

  const clearBasketBtn = document.getElementById("clear-basket-btn") as HTMLButtonElement;
  if (clearBasketBtn) {
    clearBasketBtn.onclick = () => {
      basketState.clear();
    };
  }

  const offcanvas = document.getElementById("basket-offcanvas");
  if (offcanvas) {
    offcanvas.addEventListener("show.bs.offcanvas", () => {
      basketComponent.render();
    });
  }

  return basketState;
}

export async function initGroupView(
  groupId: string | null,
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): Promise<void> {
  const api = createGroupViewApi(bonsaiApiUrl, accessToken, refreshToken);
  const basket = initBasket(api);
  if (!basket) {
    console.error("Something went wrong when initialize the basket");
    return;
  }

  const headers = document.querySelectorAll<HTMLTableCellElement>("#sample-table thead td");
  const tableConfig = { ...sampleTableConfig };
  headers.forEach((cell, idx) => {
    if (cell.textContent?.trim() === "Date") {
      tableConfig["order"] = [[idx, "desc"]];
    }
  });

  const table = initSamplesTable("sample-table", tableConfig);
  const userInfo = await api.getUserInfo();
  const user = new User(userInfo);
  initToast();
  initTooltip();

  const groupList = document.createElement("group-list") as GroupList;
  groupList.getGroupInfo = api.getGroups;
  groupList.isAdmin = user.isAdmin;

  const groupContainer = document.getElementById("group-container") as HTMLElement;
  if (groupContainer) groupContainer.appendChild(groupList);

  const addToBasketBtn = document.getElementById("add-to-basket-btn") as HTMLButtonElement;
  if (addToBasketBtn) addToBasketBtn.onclick = () => basket.addSamples(table.getSelectedRows());

  const deleteSamplesBtn = document.getElementById("remove-samples-btn") as HTMLButtonElement;
  if (deleteSamplesBtn) deleteSamplesBtn.onclick = () => deleteSelectedSamples(table, api);

  let filterBySamples = null;
  if (!(groupId === null || groupId === "")) {
    const group = await api.getGroup(groupId);
    if (group.sample_count > 0) {
      try {
        const controller = new AbortController();
        const edges = await api.getMembershipByGroups([groupId], controller.signal);
        const ids = Array.from(new Set(edges.map((e) => e.sample_id)));
        filterBySamples = ids.length === 0 ? null : ids;
      } catch (err) {
        console.error("Failed to load sample-group memberships", err);
      }
    }
  }

  const selectSimilarSamplesBtn = document.getElementById("select-similar-samples-btn") as HTMLButtonElement;
  if (selectSimilarSamplesBtn) {
    selectSimilarSamplesBtn.onclick = () =>
      getSimilarSamplesAndCheckRows(selectSimilarSamplesBtn, table, api, filterBySamples);
  }

  const groupSelectorContainer = document.getElementById("add-samples-to-group-container") as HTMLElement;
  if (groupSelectorContainer) {
    const addToGroupSelector = document.createElement("group-selector") as GroupSelector;
    addToGroupSelector.getGroupInfo = api.getGroups;
    addToGroupSelector.getSelectedSamples = table.getSelectedRows.bind(table);
    addToGroupSelector.getGroupMembership = api.getMembershipsBySamples;
    addToGroupSelector.addToGroup = api.addSamplesToGroup;
    addToGroupSelector.removeFromGroup = api.removeSamplesFromGroup;

    addToGroupSelector.addEventListener("apply:success", (ev: Event) => {
      const { groupIds, sampleIds } = (ev as CustomEvent).detail;
      throwSmallToast(`Added ${sampleIds.length} samples to ${groupIds.length} groups`, "success");
    });

    addToGroupSelector.addEventListener("apply:error", (ev: Event) => {
      const { error } = (ev as CustomEvent).detail;
      console.error("Apply error:", error);
      throwSmallToast(`An error occured: ${ev.detail}`, "error");
    });

    addToGroupSelector.addEventListener("apply:skipped", (ev: Event) => {
      const { reason } = (ev as CustomEvent).detail;
      const msg =
        reason === "empty"
          ? "No groups or samples selected"
          : reason === "no-samples"
          ? "No samples selected"
          : reason === "no-groups"
          ? "No groups selected"
          : "Nothing to do";
      throwSmallToast(msg, "warning");
    });

    groupSelectorContainer.appendChild(addToGroupSelector);
    table.getTable().on("select deselect", (e, dt, type, indexes) => {
      const selected: string[] = dt.rows(".selected").ids().toArray();
      addToGroupSelector.preselectGroupsForSamples(selected);
    });
  }

  const qcStatusForm = document.getElementById("qc-form-control") as HTMLButtonElement;
  if (qcStatusForm) {
    initSetSampleQc(
      table.getSelectedRows.bind(table),
      api.setSampleQc.bind(api),
      () => console.log("table needs to be redrawn"),
      qcStatusForm,
    );
  }

  const removeFromGroupBtn = document.getElementById("remove-from-group-btn") as HTMLButtonElement;
  if (removeFromGroupBtn) {
    removeFromGroupBtn.onclick = () => {
      const groupId: string = removeFromGroupBtn.getAttribute("data-bi-group-id");
      removeSamplesFromGroup(groupId, table, api);
    };
  }
}

// Expose for template-level initialization (backwards-compatible global)
(window as any).initGroupView = initGroupView;
