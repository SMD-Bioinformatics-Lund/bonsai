import { onEvent } from "../event-bus";
import { GroupInfo } from "../types";


function renderGroup(groupInfo: GroupInfo, isAdmin: boolean): string {
  return String.raw`
  <div class="card group-card position-relative">
    <a
      class="d-inline-block badge bage-pill bg-secondary edit-button position-absolute top-0 start-100 translate-middle"
      role="button"
      href="/"
    >
      <i class="bi bi-pencil"></i>
    </a>
  </div>
  `
}

const template = document.createElement("template");
template.innerHTML = String.raw``

/* Render cards for each group. */
export class GroupsController {
  private container : HTMLElement;

  constrictor(parentElement: HTMLElement, getGroupInfo: () => Promise<GroupInfo[]>, isAdmin: boolean) {
    parentElement.appendChild(template.content)
    this.container = parentElement.querySelector(".container") as HTMLElement;
  }

  render() {
    // create container element
    const groups: GroupInfo[] = await getGroupInfo();
    groups.forEach(group => {
      return String.raw` <div class="container">
        <h1>${group.display_name}</h1>
        <p>This is a placeholder for the groups component.</p>
      </div>`;
    });
  }
}
