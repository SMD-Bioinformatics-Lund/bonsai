import { useState, useEffect } from 'react'
import { Link } from "react-router-dom"

import './SpeciesSelection.css'
import saureus from '../images/staphylococcus_aureus.jpg'
import test from '../images/test_image.png'

import Header from '../components/Header';
import { fetchSpecies } from '../api'

const Species = () => {
  // Define states of view
  const [species, setSpecies] = useState([])

  // fetch specie information
  useEffect(() => {
    const getSpeciesDataFromServer = async () => {
      const speciesData = await fetchSpecies()
      setSpecies(speciesData)
    } 
    getSpeciesDataFromServer()
  }, [])

  return (
    <>
      <Header/>
      <div className="container">
        {species.map((specie) => ( 
          <SpeciesPanel 
            specieId={specie.species} 
            specieName={specie.label} 
            image={specie.species === 'saureus' ? saureus : test } 
            numSamples={specie.samples}
          />)
        )}
      </div>
    </>
  )
}

const SpeciesPanel = ({specieId, specieName, image, numSamples}) => {
  const url = `/${specieId}`

  return (
    <Link key={specieName} to={url}>
      <div className="card species-panel">
        <img className="card-img-top species-panel-img" src={image} alt="" />
        <div className="card-body">
          <h5 className="card-title">{specieName}</h5>
          <p className="card-text">{numSamples} isolates</p>
        </div>
      </div>
    </Link>
  )
}

export default Species
