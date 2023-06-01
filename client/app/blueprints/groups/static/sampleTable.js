export function formatSampleId(val, params, data) {
    const baseUrl = new URL(window.location.href).origin
    let element = document.createElement('a')
    let path = data.groupId ? `samples/${val}?group_id=${data.groupId}` : `samples/${val}`
    element.setAttribute('href', new URL(path, baseUrl))
    element.innerText = val
    return element.outerHTML
}

export const formatTaxonomicName = (val, params, data) => {
    let element = document.createElement('span')
    element.className = 'fw-light fst-italic'
    element.innerText = val
    return element.outerHTML
}