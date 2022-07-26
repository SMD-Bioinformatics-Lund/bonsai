import React from 'react'

export const Spinner = () => {
  return (
    <div className="d-flex justify-content-center">
      <div className="spinner-grow text-success" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
    </div>
  )
}