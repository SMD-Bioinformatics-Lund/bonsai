// get API url from environment variable
const { REACT_APP_API_URL } = process.env

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

const postCommentToSample = async (sampleId, comment) => {
  const result = await fetch(`${REACT_APP_API_URL}/samples/${sampleId}/comment`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json;charset=utf-8'},
    body: JSON.stringify(comment)
  })
  const data = await result.json()
  return data
}

const getUser = async (userName) => {
  const result = await fetch(`${REACT_APP_API_URL}/users/${userName}`)
  const data = await result.json()
  return data
}

export {fetchGroups, fetchGroupById, fetchSamples, fetchSampleById, postCommentToSample}