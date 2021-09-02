import { Link } from "react-router-dom"
import PropTypes from 'prop-types'
import "./Header.css"

const Header = ({specieName}) => {
  return (
    <header>
      <div className="logo-container">
        <span className="logo">
          <Link to="/">CGVIZ</Link>
        </span>
        { specieName && <span className="specieName">{specieName}</span> }
        <div id="login">
          <a href="">Login</a>
        </div>
      </div>
    </header>
  )
}

Header.propTypes = {
  specieName: PropTypes.string,
}

export default Header
