import React from "react";
import { useAsyncDebounce } from 'react-table'

const GlobalFilter = ({
  preGlobalFilteredRows,
  globalFilter,
  setGlobalFilter,
}) => {
  const count = preGlobalFilteredRows.length
  const [value, setValue] = React.useState(globalFilter)
  const onChange = useAsyncDebounce(value => {
    setGlobalFilter(value || undefined)
  }, 200)

  return (
    <span className="sample-search">
      <input
        className="form-control"
        value={value || ""}
        onChange={e => {
          setValue(e.target.value);
          onChange(e.target.value);
        }}
        placeholder={`Search ${count} records...`}
      />
    </span>
  )
}

const DefaultColumnFilter = ({ column: { filterValue, preFilteredRows, setFilter } }) => {
  const count = preFilteredRows.length

  return (
    <input
      className="form-control"
      value={filterValue || ""}
      onChange={e => {
        setFilter(e.target.value || undefined)
      }}
      placeholder={`${count} records...`}
    />
  )
}

const IndeterminateCheckbox = React.forwardRef(
  ({ indeterminate, ...rest }, ref) => {
    const defaultRef = React.useRef()
    const resolvedRef = ref || defaultRef

    React.useEffect(() => {
      resolvedRef.current.indeterminate = indeterminate
    }, [resolvedRef, indeterminate])

    return (
      <>
        <input type="checkbox" ref={resolvedRef} {...rest} />
      </>
    )
  }
)

// for filtering by selecting a unique option from a list
const SelectColumnFilter = ({ column: { filterValue, setFilter, preFilteredRows, id }, }) => {
  // Calculate the options for filtering from preFilterRows
  const options =  React.useMemo(() => {
    const options = new Set()
    preFilteredRows.forEach(row => {
      options.add(row.values[id])
    })
    return [...options.values()]
  }, [id, preFilteredRows])

  // render multi-select box
  return (
    <select 
      value={filterValue} 
      onChange={e => { setFilter(e.target.value || undefined) }}
      id=""
      className="form-select form-select-sm"
      >
        <option key="all" value="">All</option>
        {options.map((option, i) => (
          <option key={i} id={i} value={option}>{option}</option>
        ))}
    </select>
  )
}


const SliderColumnFilter = ({column: { filterValue, setFilter, preFilteredRows, id }}) => {
  // calculate min, max values from preFilteredRows
  const [min, max] = React.useMemo(() => {
    let min = preFilteredRows.length ? preFilteredRows[0].values[id] : 0
    let max = preFilteredRows.length ? preFilteredRows[0].values[id] : 0

    preFilteredRows.forEach(row => {
      min = Math.min(row.values[id], min)
      max = Math.max(row.values[id], max)
    })
    return [min, max]
  }, [id, preFilteredRows])
  return (
    <>
      <input
        type="range"
        min={min}
        max={max}
        value={filterValue || min}
        onChange={e => { setFilter(parseInt(e.target.value, 10)) }}
      />
      <button onClick={() => setFilter(undefined)}>Off</button>
    </>
  )
} 


const NumberRangeColumnFilter = ({ column: { filterValue=[], preFilteredRows, setFilter, id } }) => {
  const [min, max] = React.useMemo(() => {
    let min = preFilteredRows.length ? preFilteredRows[0].values[id] : 0
    let max = preFilteredRows.length ? preFilteredRows[0].values[id] : 0
    preFilteredRows.forEach(row => {
      min = Math.min(row.values[id], min)
      max = Math.max(row.values[id], max)
    })
    return [min, max]
  }, [id, preFilteredRows])

  return (
    <div className="date-picker">
      <input
        value={filterValue[0] || ''}
        type="number"
        onChange={e => {
          const val = e.target.value
          setFilter(( old=[] ) => [val ? parseInt(val, 10) : undefined, old[1]])
        }}
        placeholder={`Min (${min})`}
      />
      <input
        value={filterValue[1] || ''}
        type="number"
        onChange={e => {
          const val = e.target.value
          setFilter(( old=[] ) => [old[0], val ? parseInt(val, 10) : undefined])
        }}
        placeholder={`Max (${max})`}
      />
    </div>
  );
};


// Parse column definition and assign filter function and filter type
function parseFilterFunction(filterType, filterParam) {
  let filterFunc = {};
  switch (filterType) {
    case 'numberRange': 
    filterFunc = {Filter: NumberRangeColumnFilter, filter: filterParam};
      break;
    case 'selection': 
    filterFunc = {Filter: SelectColumnFilter, filter: filterParam};
      break;
    case 'slider': 
    filterFunc = {Filter: SliderColumnFilter, filter: filterParam};
      break;
    default:
      break
  }
  return filterFunc
}


export { parseFilterFunction, GlobalFilter, DefaultColumnFilter, IndeterminateCheckbox }
