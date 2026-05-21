import { GroupEditor } from ".";
import { GroupApi  } from "core/api";
import { SampleApi } from "core/api";
import { HttpClient } from "core/api";
import { AuthService } from "core/api";
import { InputCoreGroupInfo } from "../../core/types";
import { GroupEditorApi } from "./api";


function createGroupEditorApi(apiBaseUrl: string, accessToken: string, refreshToken: string): GroupEditorApi {
  const auth = new AuthService(apiBaseUrl);
  auth.setTokens(accessToken, refreshToken);
  const http = new HttpClient(apiBaseUrl, auth);

  const groupApi = new GroupApi(http);
  const sampleApi = new SampleApi(http);

  return {
    createGroup: (data: InputCoreGroupInfo) =>
      groupApi.createGroup(data),

    updateGroup: (id: string, data: InputCoreGroupInfo) =>
      groupApi.updateGroup(id, data),

    getGroup: (id: string) =>
      groupApi.getGroup(id),

    updateAllowedColumns: (id: string, columnIds: string[]) =>
      groupApi.updateAllowedColumns(id, columnIds),

    getAvailableColumns: sampleApi.getSummaryManifest.bind(sampleApi),
  };
}


export function initGroupEditor() {
  console.log("group editor init loaded!")

  document.addEventListener("DOMContentLoaded", () => {
    const editor = document.querySelector('group-editor') as GroupEditor;
    if (!editor) return;

    const {
      apiBaseUrl,
      accessToken,
      refreshToken,
      redirectTemplate,
    } = editor.dataset;

    editor.api = createGroupEditorApi(apiBaseUrl, accessToken, refreshToken);

    // Setup optional redirects
    editor.config = {
      redirectOnSuccess: (groupId: string) => redirectTemplate!.replace("__GROUP_ID__", groupId),
      presentation: "page"
    }
  })
}
