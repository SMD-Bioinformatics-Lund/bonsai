import React from 'react'
import { useParams } from 'react-router-dom'

export const SamplePage = () => {
  const params = useParams()

  return (
    <div><h1>Sample: {params.sampleId}</h1></div>
  )
}