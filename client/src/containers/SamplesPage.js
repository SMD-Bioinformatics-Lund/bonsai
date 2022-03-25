import { useState, useEffect } from 'react'
import { useParams } from "react-router-dom"

import Header from '../components/Header';
import IsolateTable from '../components/IsolateTable/Table';
import DetailedResultPanel from '../components/DetailedResultPanel';
import { fetchGroupById, fetchSamples } from '../api';

import 'bootstrap/dist/css/bootstrap.min.css';

const Samples = () => {
  // Define states of view
  const { group } = useParams()
  const [groupInfo, setGroupInfo] = useState(null)
  const [selectedSample, setSelectedSample] = useState(null)
  const [displayDetailedResult, setDisplayDetailedResult] = useState(false)
  const [selectedRowId, setSelectedRowId] = useState(null)

  // fetch group information with the included samples
  useEffect(() => {
    const getSpecieDataFromServer = async () => {
      const groupData = await fetchGroupById(group)
      setGroupInfo(groupData)
    }
    getSpecieDataFromServer()
  }, [group])

  const showDetailedResultFunc = ( sampleId, rowId ) => {
    if ( rowId === selectedRowId ) {
      closeDetailedResultPanelFunc()
    } else {
      const sample = groupInfo.includedSamples.filter( sample => sample.sample_id === sampleId )
      setSelectedSample(sample[0])
      setDisplayDetailedResult(true)
      setSelectedRowId(rowId)
    }
  }

  const closeDetailedResultPanelFunc = () => {
    setDisplayDetailedResult(false)
    setSelectedRowId(null)
  }

  const name = groupInfo !== null ? groupInfo.displayName : ''

  return (
    <>
      <Header groupName={name} />
      <div className="mt-5 container-fluid">
        <div className="row justify-content-start">
          <div className="col-xl-8">
            { (groupInfo !== null) && 
              <IsolateTable 
                groupInfo={groupInfo} 
                selectedRowId={selectedRowId}
                showDetailedResultFunc={showDetailedResultFunc}
              /> }
          </div>
          <div className="col-sm-4">
            { selectedSample !== null && 
            <DetailedResultPanel 
              selectedSample={selectedSample} 
              displayDetailedResult={displayDetailedResult} 
              closeDetailedResultPanelFunc={closeDetailedResultPanelFunc}
            /> }
          </div>
        </div>
      </div>
    </>
  )
}

export default Samples
