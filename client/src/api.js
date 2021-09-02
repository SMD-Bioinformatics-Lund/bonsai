const fetchSamples = async (specieName) => {
  const res = await fetch(`http://localhost:3001/samples?species=${specieName}`)
  const data = await res.json()
  return data
}

const fetchSpecies = async () => {
  const res = await fetch('http://localhost:3001/species')
  const data = await res.json()
  return data
}

const fetchSpecieByName = async (specieName) => {
  const res = await fetch(`http://localhost:3001/species?species=${specieName}&limit=1`)
  const data = await res.json()
  return data
}

export {fetchSpecies, fetchSpecieByName, fetchSamples}