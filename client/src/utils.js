export function formatPvl(data) {
  if (data === null || !data.hasOwnProperty('aribavir')) return 'NA'

  const { lukS_PV, lukF_PV } = data.aribavir
  if (typeof(lukS_PV) === 'undefined' || typeof(lukF_PV) === 'undefined') return 'NA'
  
  if (lukS_PV.present === 1 && lukF_PV.present === 1) return 'pos'
  else if ( lukS_PV.present === 1 && lukF_PV.present === 0 ) return 'neg/pos'
  else if (lukS_PV.present === 0 && lukF_PV.present === 1) return 'pos/neg'
  else return 'neg'
}

export function abbreviateSpecieName(name) {
  const [genus, specie] = name.split(" ")
  return `${genus[0]}. ${specie}`
}

export function getMetadata(data, metric) {
  if (
    data === null || 
    !data.hasOwnProperty('metadata') || 
    !data.metadata.hasOwnProperty(metric) 
    ) return '-'

  return data.metadata[metric]
}

export function range(start, end, limit = null) {
  let r = [];
  for (let i = start; i < end; i++) {
    if (limit !== null && limit + start < i) { break };
    r.push(i);
  }
  return r;
}

