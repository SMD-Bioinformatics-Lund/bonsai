import { initToast, initTooltip } from "utils/notification";
import { AuthService, HttpClient, SampleApi } from "core/api";
import { GroupApi } from "core/api";
import { initBasket } from "core/basket";
import { initSamplesTable, sampleTableConfig } from "views/samples-table";
import { deleteSelectedSamples } from "views/samples-table/utils";
import { User } from "core/user";
import { GroupList } from "../group-list";


function initApi(bonsaiApiUrl: string, accessToken: string, refreshToken: string) {
  const auth = new AuthService(bonsaiApiUrl);
  auth.setTokens(accessToken, refreshToken);
  const http = new HttpClient(bonsaiApiUrl, auth);

  const groupApi = new GroupApi(http);
  const sampleApi = new SampleApi(http);
  const userApi = new UserApi(http);

  return {
    getGroup: (id: string) =>
      groupApi.getGroup(id),

    getUser: (username: string) => userApi.getUserInfo(username),

  };
}

/* Initialize interactive elements for the group view. */
export async function initGroupView(
  groupId: string | null,
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): Promise<void> {
  // setup base functionality
  const api = initApi(bonsaiApiUrl, accessToken, refreshToken);
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
  // get logged in user
  const userInfo = await api.getUserInfo();
  const user = new User(userInfo);
  initToast();
  initTooltip();

  // render groups component
  const groupList = document.createElement("group-list") as GroupList;
  groupList.getGroupInfo = api.getGroups;
  groupList.isAdmin = user.isAdmin;

  const groupContainer = document.getElementById("group-container") as HTMLElement;
  if (groupContainer) groupContainer.appendChild(groupList);

  // attach function to DOM element
  const addToBasketBtn = document.getElementById("add-to-basket-btn") as HTMLButtonElement;
  if (addToBasketBtn) addToBasketBtn.onclick = () => basket.addSamples(table.getSelectedRows());

  const deleteSamplesBtn = document.getElementById("remove-samples-btn") as HTMLButtonElement;
  if (deleteSamplesBtn) deleteSamplesBtn.onclick = () => deleteSelectedSamples(table, api);

  // lookup samples in group if provided a groupId
  let filterBySamples = null;
  if (!(groupId === null || groupId === "")) {
    const group = await api.getGroup(groupId);
    if ( group.sample_count > 0 ) {
      try {
        const controller = new AbortController();
        const edges = await api.getMembershipByGroups([groupId], controller.signal);
        // deduplicate ids and default to null if empty
        const ids = Array.from(new Set(edges.map( e => e.sample_id )));
        filterBySamples = ids.length === 0 ? null : ids
      } catch (err) {
        console.error("Failed to load sample-group memberships", err)
      }
    }
  }