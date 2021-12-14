import { useState, useEffect } from 'react'
import { useParams } from "react-router-dom"

import Header from '../components/Header';
import IsolateTable from '../components/IsolateTable/Table';
import DetailedResultPanel from '../components/DetailedResultPanel';
import { fetchSpecieByName, fetchSamples } from '../api';

import 'bootstrap/dist/css/bootstrap.min.css';

const Samples = () => {
  // Define states of view
  const { specie } = useParams()
  const [specieInfo, setSpecieInfo] = useState(null)
  const [sampleData, setSampleData] = useState(null)
  const [selectedSample, setSelectedSample] = useState(null)
  const [displayDetailedResult, setDisplayDetailedResult] = useState(false)
  const [selectedRowId, setSelectedRowId] = useState(null)

  // fetch specie information
  useEffect(() => {
    const getSpecieDataFromServer = async () => {
      const speciesData = await fetchSpecieByName(specie)
      setSpecieInfo(speciesData[0])
    }
    getSpecieDataFromServer()
  }, [specie])

  // fetch isolate information
  useEffect(() => {
    const getSamplesFromServer = async () => {
      const samples = await fetchSamples(specie)
      setSampleData(samples)
    }
    getSamplesFromServer()
  }, [specie])


  const showDetailedResultFunc = ( sampleId, rowId ) => {
    if ( rowId === selectedRowId ) {
      closeDetailedResultPanelFunc()
    } else {
      const sample = sampleData.filter( sample => sample.sample_id === sampleId )
      setSelectedSample(sample[0])
      setDisplayDetailedResult(true)
      setSelectedRowId(rowId)
    }
  }

  const closeDetailedResultPanelFunc = () => {
    setDisplayDetailedResult(false)
    setSelectedRowId(null)
  }

  const name = specieInfo !== null ? specieInfo.label : ''

  return (
    <>
      <Header specieName={name} />
      <div className="mt-5 container-fluid">
        <div className="row justify-content-start">
          <div className="col-xl-8">
            { (specieInfo !== null && sampleData !== null) && 
              <IsolateTable 
                specieInfo={specieInfo} 
                sampleData={sampleData} 
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
