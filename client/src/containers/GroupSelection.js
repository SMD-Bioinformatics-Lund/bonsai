import { useState, useEffect } from 'react'
import { Link } from "react-router-dom"

import './GroupSelection.css'

import Header from '../components/Header';
import { fetchGroups } from '../api'

const Groups = () => {
  // Define states of view
  const [groups, setGroups] = useState([])

  // fetch group information
  useEffect(() => {
    const getGroupDataFromServer = async () => {
      const groupData = await fetchGroups()
      setGroups(groupData)
    } 
    getGroupDataFromServer()
  }, [])

  return (
    <>
      <Header/>
      <div className="container">
        {groups.map((group) => ( 
          <GroupPanel 
            groupId={group.groupId} 
            groupName={group.displayName} 
            image={group.image}
            numSamples={group.includedSamples.length}
          />)
        )}
      </div>
    </>
  )
}

const GroupPanel = ({groupId, groupName, image, numSamples}) => {
  const url = `/${groupId}`

  return (
    <Link key={groupName} to={url}>
      <div className="card group-panel">
        <img className="card-img-top group-panel-img" src={image} alt="" />
        <div className="card-body">
          <h5 className="card-title">{groupName}</h5>
          <p className="card-text">{numSamples} isolates</p>
        </div>
      </div>
    </Link>
  )
}

export default Groups