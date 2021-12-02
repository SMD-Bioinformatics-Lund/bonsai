const apiUrl = 'http://localhost:3011'

const fetchSamples = async (specieName) => {
  const res = await fetch(`${apiUrl}/samples?species=${specieName}`)
  const data = await res.json()
  return data
}

const fetchSpecies = async () => {
  const res = await fetch(`${apiUrl}/species`)
  const data = await res.json()
  return data
}

const fetchSpecieByName = async (specieName) => {
  const res = await fetch(`${apiUrl}/species?species=${specieName}&limit=1`)
  const data = await res.json()
  return data
}

export {fetchSpecies, fetchSpecieByName, fetchSamples}