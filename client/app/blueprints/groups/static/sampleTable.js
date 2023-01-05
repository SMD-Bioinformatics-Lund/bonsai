export const formatSampleId = (val, params) => {
    const baseUrl = new URL(window.location.href).origin
    let element = document.createElement('a')
    element.setAttribute('href', new URL(`samples/${val}`, baseUrl))
    element.innerText = val
    return element.outerHTML
}

export const formatTaxonomicName = (val, params) => {
    let element = document.createElement('span')
    element.className = 'fw-light fst-italic'
    element.innerText = val
    return element.outerHTML
}