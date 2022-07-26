import React from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { useGetCurrentUserQuery } from '../services/mimer'

const PrivateRoute = () => {
    const { isLoading, error } = useGetCurrentUserQuery()
    // If authorized, return an outlet that will render child elements
    // If not, return element that will navigate to login page
    if ( !isLoading ) {
      // If credentials could not be validated, probably due to old token
      if ( error !== undefined && error.status === 401 ) {
        localStorage.removeItem("token")
      }
      const isAuthenticated = !!localStorage.getItem("token")
      return isAuthenticated ? <Outlet/> : <Navigate to="/login" />;
    }
}

export default PrivateRoute