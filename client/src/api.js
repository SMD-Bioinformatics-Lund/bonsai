// get API url from environment variable
const { REACT_APP_API_URL, REACT_APP_API_KEY } = process.env

const fetchGroups = async () => {
  const res = await fetch(`${REACT_APP_API_URL}/groups`)
  const data = await res.json()
  return data
}

const fetchGroupById = async (groupId) => {
  const res = await fetch(`${REACT_APP_API_URL}/groups/${groupId}`)
  const data = await res.json()
  return data
}

const fetchSamples = async () => {
  const res = await fetch(`${REACT_APP_API_URL}/samples`)
  const data = await res.json()
  return data
}

const fetchSampleById = async (sampleId) => {
  const res = await fetch(`${REACT_APP_API_URL}/samples/${sampleId}`)
  const data = await res.json()
  return data
}

export {fetchGroups, fetchGroupById, fetchSamples, fetchSampleById}