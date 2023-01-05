const addSampleToList = (sampleId) => {
    sampleListItem = document.getElementById('sample-list-item-template').content.firstElementChild.cloneNode(true)
    sampleListItem.childNodes[0].nodeValue = sampleId
    document.getElementById('added-samples-list').appendChild(sampleListItem)
}

const addNewColumnToList = (element) => {
    columnListItem = document.getElementById('column-list-item-template').content.firstElementChild.cloneNode(true)
    // populate template with values from form
    for (const id of ['#input-col-label', '#input-col-data-type', '#input-col-data-path']) {
        columnListItem.querySelector(id).value = element.querySelector(id).value
    }
    for (const id of ['#sortable-check', '#searchable-check', '#hidden-check']) {
        columnListItem.querySelector(id).checked = element.querySelector(id).checked
    }
    document.getElementById('added-columns-list').appendChild(columnListItem)
}

const updateGroup = (event) => {
    // collect information to be sumbitted
    const groupId = document.getElementById('input-group-id').value
    const groupName = document.getElementById('input-group-name').value
    // get all cards
    const list = document.querySelectorAll('.column-card')
    const groupColumns = Array.from(list).map(column => {
            return {
                label: column.querySelector('#input-col-label').value,
                type: column.querySelector('#input-col-data-type').value,
                path: column.querySelector('#input-col-data-path').value,
                sortable: column.querySelector('#sortable-check').checked,
                searchable: column.querySelector('#searchable-check').checked,
                hidden: column.querySelector('#hidden-check').checked
            }
    })
    const samplesList = document.querySelectorAll('#added-samples-list li')
    const addedSamples = Array.from(samplesList).map(li => li.getAttribute('key'))
    // store updatd fields as json in input
    const result = event.target.querySelector('input[name="input-update-group"]')
    result.value = JSON.stringify({
        groupId: groupId, 
        displayName: groupName,
        tableColumns: groupColumns,
        includedSamples: addedSamples
    })
}