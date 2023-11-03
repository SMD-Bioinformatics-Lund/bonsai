// functions relating to the sample basket and navbar
async function startClusteringJob() {
}

// cluter all samples in basket
async function clusterSamplesInBasket(element) {
    const typingMethod = element.getAttribute("data-bi-typing-method") 
    // base dropdown element
    const baseElement = document.querySelector("#basket-cluster-samples")
    const btn = baseElement.querySelector(".btn")
    const treeApiRoute = baseElement.getAttribute("data-bi-tree-route") 
    const sampleIds = JSON.parse(baseElement.querySelector("input[name=sample-ids]").value)
    // construct body to pass
    let body
    switch (typingMethod) {
        case "cgmlst":
            body = {
                sample_ids: sampleIds,
                typing_method: typingMethod,
                cluster_method: "MSTreeV2",
            }
            break
        case "mlst":
            body = {
                sample_ids: sampleIds,
                typing_method: typingMethod,
                cluster_method: "MSTreeV2",
             }
             break
        case "minhash":
            body = {
                sample_ids: sampleIds,
                typing_method: typingMethod,
            }
            break
    }
    // submit job to API
    showSpinner(btn)
    try {
        const response = await fetch(treeApiRoute, {
            method: "POST",
            headers: { 
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        })
        if (!response.ok) {
            throw new Error("Network response was not OK!")
        }
        const jobInfo = await response.json()
        // inform user that clustering has started
        throwSmallToast(`Clustering samples: ${sampleIds.length}`, "info")

        // start polling for updates
        let result = await poll(
            async () => fetchJobStatus(jobInfo.id),  // GET job status
            validateJobStatus,  // validator
            resultParser,       // parse results
            3000                // interval time
        )
        hideSpinner(btn)
        // open dendrogram
        drawDendrogram(result, sampleId)
    } catch (error) {
        throwSmallToast('A problem occured during clustering', 'error')
        hideSpinner(btn)
        console.log(`A problem occured during clustering, ${error}`)
    }
}

const removeSampleFromBasket = (btn) => {
    // remove sample id from basket
    // update basket counter by making request to front-end api, 
    const body = {
        sample_id: btn.parentElement.querySelector('h6').id
    }
    fetch(`${baseUrl}/api/basket/remove`, {
        method: "POST",
        body: JSON.stringify(body),
        headers: {
            'Accept': 'application/json', 
            'Content-Type': 'application/json' 
        },
        credentials: 'same-origin'
    }).then(response => {
        // remove card from list
        btn.parentElement.parentElement.remove()
        // decrease count
        const counter = document.querySelector("#samples-in-basket-counter")
        const num = Number(counter.innerText)
        if ( num < 1 ) {
            document.querySelector("#samples-in-basket-badge").hidden = true
        } else {
            counter.innerText = num - 1
        }
    })
}

const removeAllSamplesFromBasket = () => {
    // kick out all samples from the basket
    // update basket counter by making request to front-end api, 
    const body = {
        remove_all: true
    }
    fetch(`${baseUrl}/api/basket/remove`, {
        method: "POST",
        body: JSON.stringify(body),
        headers: {
            'Accept': 'application/json', 
            'Content-Type': 'application/json' 
        },
        credentials: 'same-origin'
    }).then(response => {
        document.querySelectorAll('.sample_in_basket').forEach(e => e.remove());
        const counter = document.querySelector("#samples-in-basket-counter")
        counter.innerText = 0
        document.querySelector("#samples-in-basket-badge").hidden = true
    })
}
