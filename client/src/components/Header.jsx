import { Link } from "react-router-dom"
import PropTypes from 'prop-types'
import "./Header.css"

const Header = ({groupName}) => {
  return (
    <header>
      <div className="logo-container">
        <span className="logo">
          <Link to="/">CGVIZ</Link>
        </span>
        { groupName && <span className="groupName">{groupName}</span> }
        <div id="login">
          <a href="">Login</a>
        </div>
      </div>
    </header>
  )
}

Header.propTypes = {
  groupName: PropTypes.string,
}

export default Header
