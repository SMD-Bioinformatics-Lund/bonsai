// functions for polling job status
async function poll(fn, fnCondition, resultParser, ms) {
    // utility function for polling data
    let result = await fn()
    while (fnCondition(result)) {
        await wait(ms)
        result = await fn()
    }
    return resultParser(result)
}

function wait(ms = 2000) {
    // wait between fetch jobs
    return new Promise(resolve => {
        setTimeout(resolve, ms)
    })
}

let fetchJobStatus = async (jobId) => {
    // fetch job status from bonsai api
    const response = await fetch(`${apiURL}/job/status/${jobId}`)
    return {status: response.status, data: await response.json()}
}

function validateJobStatus(result) {
    // check job status
    // returns true if run is invalid
    let isValid = false
    const jobInfo = result.data
    if ( jobInfo.status === "finished" ) {
        // if job has finished report result
        isValid = true
    } else if ( jobInfo.status === "failed" ) {
        // if job failed raise error
        throw new Error(`Job failed: ${jobInfo.result}`)
        isValid = true
    } 
    console.log(`Job status: ${jobInfo.status}; is valid ${isValid}`)
    return !isValid
}

// get result from job info object
const resultParser = (result) => result.data.result

// functions for hide/ showing spinner
const showSpinner = (element) => {
    // show spinner and hide content
    const content = element.querySelector('.content')
    const spinner = element.querySelector('.loading')
    content.classList.add("d-none")
    content.disabled = true
    spinner.classList.remove("d-none")
}

const hideSpinner = (element) => {
    // hide spinner and show content
    const content = element.querySelector('.content')
    const spinner = element.querySelector('.loading')
    content.classList.remove("d-none")
    content.disabled = false
    spinner.classList.add("d-none")
}