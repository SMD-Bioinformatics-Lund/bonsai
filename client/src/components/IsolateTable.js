import React from "react";
import PropTypes from 'prop-types'

import { formatPvl, range } from '../utils'
import { useTable, usePagination, useSortBy, useFilters, useGlobalFilter, useAsyncDebounce, useRowSelect } from 'react-table'

//import Table from 'react-bootstrap/Table';
import { SortUp, SortDown, ChevronDoubleRight, ChevronRight, ChevronLeft, ChevronDoubleLeft } from 'react-bootstrap-icons';
import 'bootstrap/dist/css/bootstrap.min.css';
import '/trannel/proj/cgviz/client/src/components/IsolateTable.css';

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


function cellFormat(dataType) {
  let formatFunc;
  switch ( dataType ) {
    case 'pvl': 
      formatFunc = {Cell: ({ cell: value }) => <PvlTyping value={value}/>};
      break;
    default:
      formatFunc = {}
      break
  }
  return formatFunc
}


const PvlTyping = ({ value }) => {
  // Create PVL typing badge
 let badgeColor
  switch (value) {
    case 'pos':
      badgeColor = 'badge-success';
      break;
    case 'neg':
      badgeColor = 'badge-warning';
      break;
    case 'pos/neg':
      badgeColor = 'badge-warning';
      break;
    case 'neg/pos':
      badgeColor = 'badge-warning';
      break;
    default:
      badgeColor = 'badge-secondary'
  }
  return (<span className={`badge ${badgeColor}`}>{value}</span>);
}




const TableComponent = ({ columns, data }) => {

  const defaultColumn = React.useMemo(() => ({
    // Default filter UI
    Filter: DefaultColumnFilter,
  }), [])

  const table = useTable({
    columns, data, defaultColumn, initialState: { pageIndex: 0, pageSize: 5 }
  }, useFilters, useGlobalFilter, useSortBy, usePagination, useRowSelect, hooks => {
    hooks.visibleColumns.push(columns => [
      {
        id: 'selection',
        
        Header: ({ getToggleAllRowsSelectedProps }) => (
          <div>
            <IndeterminateCheckbox {...getToggleAllRowsSelectedProps()} />
          </div>
        ),
        Cell: ({ row }) => (
          <div>
            <IndeterminateCheckbox {...row.getToggleRowSelectedProps()} />
          </div>
        ),
      },
      ...columns,
    ])
  })

  const {
    getTableProps,
    getTableBodyProps,
    headerGroups,
    rows,
    prepareRow,
    selectedFlatRows,
    page,
    state,
    preGlobalFilteredRows,
    setGlobalFilter,
  } = table

  return (
    <>
      <div className="row justify-content-start">
        <div className="col-sm-8">
          <GlobalFilter
            preGlobalFilteredRows={preGlobalFilteredRows}
            globalFilter={state.globalFilter}
            setGlobalFilter={setGlobalFilter}
          />
        </div>
        <div className="col-sm-2 align-self-end">
          <span>{selectedFlatRows.length} of {rows.length} samples</span>
        </div>
      </div>
      <div className="row">
        <div className="col-lg-12">
          <table className="table table-hover" {...getTableProps()}>
            <thead>
              {headerGroups.map((headerGroup, i) => (
                <tr key={i} {...headerGroup.getHeaderGroupProps()}>
                  {headerGroup.headers.map((column, i) => (
                    <th key={i} {...column.getHeaderProps(column.getSortByToggleProps())}>
                      {column.render('Header')}
                      {/* Render icons when sorting the columns */}
                      <span>
                        {column.isSorted ? column.isSortedDesc ? <SortUp /> : <SortDown /> : ''}
                      </span>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody {...getTableBodyProps()}>
              {page.map((row, i) => {
                prepareRow(row)
                return (
                  <tr key={i}>
                    {row.cells.map(cell => {
                      return <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                    })}
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              {headerGroups.map(headerGroup => (
              <tr {...headerGroup.getHeaderGroupProps()}>
                {headerGroup.headers.map((column, i) => (
                  <th key={i}>
                    {/* Render columns filter UI */}
                    <div>{column.canFilter ? column.render('Filter') : null}</div>
                  </th>
                ))}
              </tr>
              ))}
            </tfoot>
          </table>
        </div>
      </div>
      <div className="row">
        <div className="col-md-8"><PaginationSection table={table} state={state} /></div>
      </div>
    </>
  )
}

const PaginationSection = ({ table, state }) => {
  const {
    canPreviousPage,
    canNextPage,
    pageOptions,
    pageCount,
    gotoPage,
    nextPage,
    previousPage,
  } = table
  const { pageIndex } = state

  const prevDisabled = !canPreviousPage ? " disabled" : ""
  const nextDisabled = !canNextPage ? " disabled" : ""

  const start = pageIndex === 0 ? pageIndex : pageIndex - 1
  const quickSelectPages = range(start, pageOptions.length, 3)

  return (
    <ul className="pagination pagination-sm">
      <li key="1" className={`page-item ${prevDisabled}`} onClick={() => gotoPage(0)}>
        <a className="page-link"><ChevronDoubleLeft /> </a>
      </li>
      <li key="2" className={`page-item ${prevDisabled}`} onClick={() => previousPage()}>
        <a className="page-link"><ChevronLeft /></a>
      </li>
      {quickSelectPages.map(pageNo =>
        <li key="3" className={`page-item ${pageNo === pageIndex ? 'active' : ''}`} onClick={() => gotoPage(pageNo)}>
          <a className="page-link">{pageNo + 1}</a>
        </li>
      )}
      <li key="4" className={`page-item ${nextDisabled}`} onClick={() => nextPage()}>
        <a className="page-link"><ChevronRight /></a>
      </li>
      <li key="5" className={`page-item ${nextDisabled}`} onClick={() => gotoPage(pageCount - 1)}>
        <a className="page-link"><ChevronDoubleRight /></a>
      </li>
      <li key="6">
        <a className="page-link">
          Page{' '}
          <strong>
            {pageIndex + 1} of {pageOptions.length}
          </strong>
        </a>
      </li>
    </ul>
  )
}

const IsoalteTable = ({ specieInfo, sampleData }) => {
  // create header and data
  // ...cellFormat(column.name),
  const columns = specieInfo
    .fields
    .filter(column => column.hidden === 0)
    .map(column => { 
      return { 
        Header: column.label, 
        accessor: column.name,
        ...parseFilterFunction(column.filterType, column.filterParam),
        disableFilters: !column.filterable,
      } 
    })
  console.log(columns)

  const data = sampleData.map(sample => {
    return {
      sampleId: sample.sample_id,
      specie: sample.top_brakken.top_species,
      mlstSt: sample.mlst.sequence_type,
      pvl: formatPvl(sample),
      date: sample.creation_date,
      qc: sample.metadata.QC,
      location: sample.metadata.location,
      outbreak: null,
      comment: null,
    }
  })

  return (
    <div className="table-container">
      <TableComponent columns={columns} data={data} />
    </div>
  )
}

TableComponent.propTypes = {
  columns: PropTypes.array.isRequired,
  data: PropTypes.array.isRequired,
}

export default IsoalteTable
