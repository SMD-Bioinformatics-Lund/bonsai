export function formatPvl(data) {
  if (data === null || !data.hasOwnProperty('aribavir')) return 'NA'

  const { lukS_PV, lukF_PV } = data.aribavir
  if (typeof(lukS_PV) === 'undefined' || typeof(lukF_PV) === 'undefined') return 'NA'
  
  if (lukS_PV.present === 1 && lukF_PV.present === 1) return 'pos'
  else if (lukS_PV === 1) return 'neg/pos'
  else if (lukF_PV === 1) return 'pos/neg'
  else return 'neg'
}

export function getMetadata(data, metric) {
  if (
    data === null || 
    !data.hasOwnProperty('metadata') || 
    !data.metadata.hasOwnProperty(metric) 
    ) return '-'

  return data.metadata[metric]
}
