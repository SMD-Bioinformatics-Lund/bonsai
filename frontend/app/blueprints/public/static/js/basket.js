// functions relating to the sample basket and navbar

// cluter all samples in basket
const clusterSamplesInBasket = (element) => {
    const treeApiRoute = element.parentElement.getAttribute("data-bi-tree-route") 
    const sampleIds = JSON.parse(element.parentElement.querySelector("input").value)
    debugger
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
