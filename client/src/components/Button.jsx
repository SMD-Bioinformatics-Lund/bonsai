import PropTypes from 'prop-types'

const Button = ({text, classNames}) => {
  const buttonClassNames = ['btn', ...classNames].join(' ')

  return (
    <button className={buttonClassNames}>{text}</button>
  )
}

Button.defaultProps = {
  classNames: [],
}

Button.propTypes = {
  text: PropTypes.string.isRequired,
  classNames: PropTypes.array,
  //onClick: PropTypes.func.isRequired,
}

export default Button