import './GroupSelection.css'

import { Spinner } from '../components/Spinner';
import { GroupPanelContainer } from "../components/GroupView";
import { connect } from 'react-redux';
import { useGetGroupsQuery } from '../services/mimer';

const Groups = () => {
  // Define states of view
  const { data = [], error, isLoading } = useGetGroupsQuery()

  return (
    <div className='d-flex justify-content-center'>
      { isLoading ? <Spinner/> : <GroupPanelContainer/>}
      { error ? (<div>An error occured: {error.status}</div>) : ""}
    </div>
  )
}

export default Groups;