import React from 'react'
import { Link, Outlet } from "react-router-dom"
import { useGetGroupsQuery } from '../services/mimer';


export const GroupPanelContainer = () => {
  // Define states of view
  const { data = [], error, isLoading } = useGetGroupsQuery()

  return (
    <div className="container">
      {data.map((group) => (
        <GroupPanel
          key={group.groupId}
          groupId={group.groupId}
          groupName={group.displayName}
          image={group.image}
          numSamples={group.includedSamples.length}
        />)
      )}
    </div>
  )
}


const GroupPanel = ({ groupId, groupName, image, numSamples }) => {
  const url = `/groups/${groupId}`

  return (
    <Link key={groupId} to={url}>
      <div className="card group-panel">
        <div className="card-body">
          <h5 className="card-title">{groupName}</h5>
          <p className="card-text">{numSamples} isolates</p>
        </div>
      </div>
    </Link>
  )
}

export default GroupPanelContainer;