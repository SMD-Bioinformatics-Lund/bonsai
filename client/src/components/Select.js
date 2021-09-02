const Select = ({classNames, onChange, options}) => {
  // {options.map((option) => (<option {option.selected ? 'selected'}>{option.label}</option>))}
  return (
    <select classNames={classNames} onChange={onChange}>
      {options.map((opt) => (<option value={opt.value}>{opt.label}</option>))}
    </select>
  )
}

export default Select