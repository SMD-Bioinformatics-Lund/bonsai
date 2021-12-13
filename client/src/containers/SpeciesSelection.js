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
          numSamples={specie.samples}/>)
        )}
      </div>
    </>
  )
}

const SpeciesPanel = ({specieId, specieName, image, numSamples}) => {
  const url = `/${specieId}`

  return (
    <Link key={specieName} to={url}>
      <div className="species-panel">
        <img src={image} alt="" />
        <h3>{specieName}</h3>
        <p>{numSamples} isolates</p>
      </div>
    </Link>
  )
}

export default Species
