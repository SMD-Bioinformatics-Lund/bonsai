import React from 'react'
import { useParams } from 'react-router-dom'

export const ErrorPage = () => {
  const params = useParams()
  return (
    <div>
      <h1>Page could not be found</h1>
      <p>The page {params} could not be found</p>
    </div>
  )
}
