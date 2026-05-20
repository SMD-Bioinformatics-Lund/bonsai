import { GroupEditor } from ".";
import { GroupApi  } from "../../core/api";
import { HttpClient } from "../../core/api";
import { AuthService } from "../../core/api";
import { InputCoreGroupInfo } from "../../core/types";
import { GroupEditorApi } from "./api";

document.addEventListener("DOMContentLoaded", () => {
  const editor = document.querySelector('group-editor') as GroupEditor;

  const redirectTemplate = editor.dataset.redirectTemplate;
  if (!editor) {
    console.log("<group-editor> was not found in DOM")
    return;
  };

  // setup API
  const auth = new AuthService("/api")
  const http = new HttpClient("/api", auth)
  const groupApi = new GroupApi(http)

  const api: GroupEditorApi = {
    createGroup: (data: InputCoreGroupInfo) => api.createGroup(data),
    updateGroup: (id: string, data: InputCoreGroupInfo) => api.updateGroup(id, data),
    getGroup: (id: string) => groupApi.getGroup(id),
    updateAllowedColumns: (id: string, columnIds: string[]) => api.updateAllowedColumns(id, columnIds),
  }

  editor.api = api;

  // Setup optional redirects
  editor.config = {
    redirectOnSuccess: (groupId: string) => redirectTemplate!.replace("__GROUP_ID__", groupId),
    presentation: "page"
  }
})