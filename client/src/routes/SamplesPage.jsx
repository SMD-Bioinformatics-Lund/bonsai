import { useState } from 'react'
import { useParams } from "react-router-dom"

import IsolateTable from '../components/IsolateTable/Table';
import DetailedResultPanel from '../components/DetailedResultPanel';

import { useGetGroupByIdQuery } from '../services/mimer';
import { Spinner } from '../components/Spinner';
import { toast, ToastContainer } from 'react-toastify'

const Samples = () => {
  // Define states of view
  const params = useParams()
  // get group info
  const { data, error, isLoading } = useGetGroupByIdQuery(params.groupId)
  const [selectedRowId, setSelectedRowId] = useState(null)

  return (
    <div className="mt-5 container-fluid">
      <div className="row justify-content-start">
        <div className="col-xl-12">
          {isLoading ? 
            <Spinner /> : 
            <IsolateTable 
              groupInfo={data} 
              selectedRowId={selectedRowId}
            />
          }
          {error ?  
            toast.error(error, {
              position: 'top-center',
              autoClose: 5000,
              hideProgressBar: false,
              closeOnClick: true,
              pauseOnHover: true
              }) : ""}
        </div>
      </div>
      <ToastContainer/>
    </div>
  )
}

export default Samples
