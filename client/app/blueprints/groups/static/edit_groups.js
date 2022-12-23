const addSampleToList = (sampleId) => {
    sampleListItem = document.getElementById('sample-list-item-template').content.firstElementChild.cloneNode(true)
    sampleListItem.childNodes[0].nodeValue = sampleId
    document.getElementById('added-samples-list').appendChild(sampleListItem)
}

const addNewColumnToList = (element) => {
    columnListItem = document.getElementById('column-list-item-template').content.firstElementChild.cloneNode(true)
    document.getElementById('added-columns-list').appendChild(columnListItem)
}