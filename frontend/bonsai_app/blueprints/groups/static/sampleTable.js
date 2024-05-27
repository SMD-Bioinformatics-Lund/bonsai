import { JSONPath } from "./index-browser-esm.min.js"

export const formatOpenSampleBtn = (val, params, data) => {
    // create base url by stripping the last entry of the path
    // in case bonsai is not hosted under the root path
    const groupNamePos = window.location.pathname.split('/').indexOf('groups')
    const baseUrl = window.location.pathname.split('/').slice(0, groupNamePos).join('/') 
    console.log(`${window.location.pathname} --> ${baseUrl}`)
    let element = document.createElement('a')
    let path = data.groupId ? `sample/${val.sample_id}?group_id=${data.groupId}` : `sample/${val.sample_id}`
    element.setAttribute('href', `${baseUrl}/${path}`)
    element.classList.add('btn', 'btn-sm', 'btn-dark', 'br-table-link')
    //element.classList.add('badge', 'text-bg-info', 'rounded-pill', 'p-1')
    element.innerText = 'Open'
    return element.outerHTML
}

export const formatSampleId = (val, params, data) => {
    // create base url by stripping the last entry of the path
    // in case bonsai is not hosted under the root path
    const groupNamePos = window.location.pathname.split('/').indexOf('groups')
    const baseUrl = window.location.pathname.split('/').slice(0, groupNamePos).join('/') 
    console.log(`${window.location.pathname} --> ${baseUrl}`)
    let element = document.createElement('a')
    let path = data.groupId ? `sample/${val.sample_id}?group_id=${data.groupId}` : `sample/${val.sample_id}`
    element.setAttribute('href', `${baseUrl}/${path}`)
    element.classList.add('br-link')
    element.innerText = val.name
    return element.outerHTML
}

export const formatTaxonomicName = (val, params, data) => {
    let element = document.createElement('span')
    element.className = 'fw-light fst-italic'
    element.innerText = val
    return element.outerHTML
}

export const formatTag = (val, params, data) => {
    let elements = val.map(tag => {
        let element = document.createElement('span')
        element.className = `badge text-bg-${tag.severity} p-1 me-1`
        element.innerText = tag.label
        return element.outerHTML
    })
    return elements.join('')
}

export async function getDefaultCols (apiUrl) {
    const resp = await fetch(`${apiUrl}/groups/default/columns`)
    return await resp.json()
}

export const formatTableColumn = col => {
    return {
        field: col.id,
        text: col.label,
        path: col.path,
        sortable: col.sortable,
        hidden: col.hidden,
        render: col.type.toLowerCase() === 'string' ? null : col.type.toLowerCase(),
    }
}

export const getTableSampleData = (sample, tableConfig) => {
    // add sample id to colums with sampleid type
    const check_sampleid = (col) => {
        let result
        if (col.type == "sample_btn") {
            result = {
                sample_id: JSONPath({path: "$.sample_id", json: sample})[0], 
                name: JSONPath({path: col.path, json: sample})[0]
            }
        } else {
            result = JSONPath({path: col.path, json: sample})[0]
        }
        return result
    }

    let columns = tableConfig.reduce((acc, col) => ({ ...acc, [col.id]:  check_sampleid(col)}), {}) 
    columns["recid"] = sample["sample_id"]
    return columns
}