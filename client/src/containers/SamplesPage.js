import { useState, useEffect } from 'react'
import { useParams } from "react-router-dom"

import Header from '../components/Header';
import IsolateTable from '../components/IsolateTable';
import { fetchSpecieByName, fetchSamples } from '../api';

import 'bootstrap/dist/css/bootstrap.min.css';

const Samples = () => {
  // Define states of view
  const { specie } = useParams()
  const [specieInfo, setSpecieInfo] = useState(null)
  const [sampleData, setSampleData] = useState(null)

  // fetch specie information
  useEffect(() => {
    const getSpecieDataFromServer = async () => {
      const speciesData = await fetchSpecieByName(specie)
      setSpecieInfo(speciesData[0])
    }
    getSpecieDataFromServer()
  }, [])

  // fetch isolate information
  useEffect(() => {
    const getSamplesFromServer = async () => {
      const samples = await fetchSamples(specie)
      setSampleData(samples)
    }
    getSamplesFromServer()
  }, [])

  const name = specieInfo !== null ? specieInfo.label : ''

  return (
    <>
      <Header specieName={name} />
      <div className="container-fluid">
        <div className="row justify-content-start">
          <div className="col-xl-8">
            { (specieInfo !== null && sampleData !== null) && 
              <IsolateTable 
              specieInfo={specieInfo} 
              sampleData={sampleData} 
              /> }
          </div>
          <div className="col-sm-4">
            foo bar
          </div>
        </div>
      </div>
    </>
  )
}

export default Samples
