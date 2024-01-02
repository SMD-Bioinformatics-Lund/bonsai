const addSampleToList = (sampleId) => {
    sampleListItem = document.getElementById('sample-list-item-template').content.firstElementChild.cloneNode(true)
    sampleListItem.childNodes[0].nodeValue = sampleId
    sampleListItem.setAttribute("key", sampleId)
    document.getElementById('added-samples-list').appendChild(sampleListItem)
}

const addGeneToList = (geneName, categroy) => {
    sampleListItem = document.getElementById('sample-list-item-template').content.firstElementChild.cloneNode(true)
    sampleListItem.childNodes[0].nodeValue = geneName
    sampleListItem.setAttribute("key", geneName)
    const geneList = document.getElementById(`${categroy}-list`)
    geneList.parentElement.parentElement.hidden = false
    geneList.appendChild(sampleListItem)
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


function validateFilledInput(input, minLength = 1, maxLength = null) {
    // validate that input element is filled
    let isError = false
    let errorMsg = ""
    // test min length
    if ( input.value === "" || input.value.length < minLength ) {
        isError = true
        errorMsg = `input must be longer than ${minLength} characters`
    // test max length
    } else if ( maxLength !== null && maxLength < input.value.length ) {
        isError = true
        errorMsg = `input can't be longer than ${maxLength} characters`
    }
    // thow error
    if ( isError ) {
        input.classList.add("is-invalid")
        input.parentElement.querySelector('.invalid-feedback').innerText = errorMsg
        throw new Error(`Input faild validation: ${errorMsg}`)
    }
}


const updateGroup = (event, method) => {
    // collect information to be sumbitted
    let groupId = document.getElementById('input-group-id')
    let groupName = document.getElementById('input-group-name')
    let groupDesc = document.getElementById('input-group-description')
    let failedValidation = false // controller for validation
    // validate group id
    try {
        validateFilledInput(groupId, 5)
        groupId = groupId.value
    } catch (error) {
        console.log(error) // throw error
        failedValidation = true
    }
    // validate group name
    try {
        validateFilledInput(groupName, 1, 45)
        groupName = groupName.value
    } catch (error) {
        console.log(error) // throw error
        failedValidation = true
    }
    // break execution of input failed validation
    if (failedValidation) {
        event.preventDefault()
        event.stopPropagation()
        // stop submit event and break function execution
        return
    }
    // parse selected columns
    const list = document.querySelectorAll('.column-card')
    const groupColumns = Array
        .from(list)
        .filter(column => column.querySelector('input[role="switch"]').checked)
        .map(column => {
            return {
                label: column['dataset'].label,
                type: column['dataset'].dtype,
                path: column['dataset'].path,
                sortable: column.querySelector('input[name="sortable"]').checked,
                searchable: column.querySelector('input[name="searchable"]').checked,
                hidden: column.querySelector('input[name="hidden"]').checked
            }
        })
    // parse samples and validated genes
    const samplesList = document.querySelectorAll('#added-samples-list li')
    let validatedGenes = {}
    for (const list of document.querySelectorAll('.validated-genes-list')) {
        const geneName = list.id.replace("-list", "") 
        const items = Array.from(list.querySelectorAll("li")).map(li => li.getAttribute("key"))
        if ( items.length > 0) validatedGenes[geneName] = items
    }
    const addedSamples = Array.from(samplesList).map(li => li.getAttribute('key'))
    // store updatd fields as json in input
    const result = event.target.querySelector(`input[name="input-${method}-group"]`)
    result.value = JSON.stringify({
        group_id: groupId, 
        display_name: groupName,
        description: groupDesc.value,
        table_columns: groupColumns,
        validated_genes: validatedGenes,
        included_samples: addedSamples
    })
}


const toggleDisabled = (input) => {
    const parent = input.parentElement.parentElement.parentElement
    // select all inputs
    parent.querySelectorAll('.display-params-input input').forEach(elem => elem.disabled = !input.checked)
    if ( input.checked ) {
        parent.classList.add('active')
    } else {
        parent.classList.remove('active')
    }
}