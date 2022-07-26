import { Link, useMatch, useParams, useResolvedPath } from "react-router-dom"
import PropTypes from 'prop-types'
import "./Navbar.css"
//import {useGetUserByUsernameQuery} from '../services/api'
import { useDispatch, useSelector } from "react-redux"
import { useGetCurrentUserQuery } from "../services/mimer"
import { logout } from "../reducers/auth"

export const Navbar = () => {
  const isLoggedIn = useSelector((state) => state.auth.token)

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-success bg-opacity-25">
      <div className="container-fluid">
        <Link to="/" className="navbar-brand">BaktAna</Link>
        <button 
          className="navbar-toggler" 
          type="button" 
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
          >
            <span className="navbar-toggler-icon"/>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0">
              <NavbarLink children={"Home"} to={'/'} className="nav-link"/>
              <NavbarLink children={"Groups"} to={'/groups'} className="nav-link"/>
              <NavbarLink children={"Locations"} to={'/locations'} className="nav-link disabled"/>
            </ul>
            <ul className="navbar-nav mb-2 mb-lg-0 ml-2">
              { isLoggedIn ? 
                <UserDropdown/> : 
                <Link to={'/login'} className="btn btn-sm btn-outline-success">Login</Link>
              }
            </ul>
          </div>
      </div>
    </nav>
  )
}

const logoutUser = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  // remove token from local storage
  localStorage.removeItem("token")
  // remove token from state
  dispatch(logout)
  // navigate to home
  navigate('/login')
}

const UserDropdown = () => {
  const { data, isLoading, isError } = useGetCurrentUserQuery()
  return (
    <li className="nav-item dropdown">
      { 
        isLoading || isError ? "" : 
        <>
          <a 
            id="navbarDropdown"
            className="nav-link dropdown-toggle" 
            role="button"
            href="#" 
            data-bs-toggle="dropdown"
            data-bs-display="static"
            aria-expanded="false"
            >
              <span className="user-alias-container bg-dark text-light text-center text-uppercase fs-6 fw-lighter font-monospace">
                {data.firstName[0] + data.lastName[0]}
              </span>
          </a>
          <ul className="dropdown-menu dropdown-menu-lg-end" aria-labelledby="navbarDropdown">
            <li><a className="dropdown-item disabled" href="#">Profile</a></li>
            <li><a className="dropdown-item disabled" href="#">Settings</a></li>
            <li><hr className="dropdown-divider"/></li>
            <li><a className="dropdown-item" href="#" onClick={logoutUser}>Log out</a></li>
          </ul>
        </>
      }
    </li>
  )
}

const NavbarLink = ({children, to, className="", ...props}) => {
  const resolved = useResolvedPath(to)
  const match = useMatch({ path: resolved.pathname, end: true})
  className += match ? " active" : ""
  return (
    <li className="nav-item">
      <Link 
        to={to}
        className={className}
        {...props}
      >
        {children}
      </Link>
    </li>
  )
}

Navbar.propTypes = {
  groupName: PropTypes.string,
}

export default Navbar
