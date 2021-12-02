import React from "react";
import PropTypes from 'prop-types'

import { formatPvl, getMetadata } from '../utils'
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
      Search:{' '}
      <input
        className="form-control"
        value={value || ""}
        onChange={e => {
          setValue(e.target.value);
          onChange(e.target.value);
        }}
        placeholder={`${count} records...`}
      />
    </span>
  )
}

const DefaultColumnFilter = ({ column: { filterValue, preFilterRows, setFilter } }) => {
  const count = preFilterRows.length

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

const TableComponent = ({ columns, data }) => {

  const defaultColumn = React.useMemo(() => ({
    // Default filter UI
    Filter: DefaultColumnFilter,
  }), {})

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
      </div>
      <div className="row">
        <div className="col-lg-12">
          <table className="table table-hover" {...getTableProps()}>
            <thead>
              {headerGroups.map(headerGroup => (
                <tr {...headerGroup.getHeaderGroupProps()}>
                  {headerGroup.headers.map(column => (
                    <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                      {column.render('Header')}
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
                  <tr>
                    {row.cells.map(cell => {
                      return <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
      <div className="row">
        <div className="col-md-8"><PaginationSection table={table} state={state} /></div>
      </div>
    </>
  )
}

function range(start, end, limit = null) {
  let r = [];
  for (let i = start; i < end; i++) {
    if (limit !== null && limit + start < i) { break };
    r.push(i);
  }
  return r;
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
      <li className={`page-item ${prevDisabled}`} onClick={() => gotoPage(0)}>
        <a className="page-link"><ChevronDoubleLeft /> </a>
      </li>
      <li className={`page-item ${prevDisabled}`} onClick={() => previousPage()}>
        <a className="page-link"><ChevronLeft /></a>
      </li>
      {quickSelectPages.map(pageNo =>
        <li className={`page-item ${pageNo === pageIndex ? 'active' : ''}`} onClick={() => gotoPage(pageNo)}>
          <a className="page-link">{pageNo + 1}</a>
        </li>
      )}
      <li className={`page-item ${nextDisabled}`} onClick={() => nextPage()}>
        <a className="page-link"><ChevronRight /></a>
      </li>
      <li className={`page-item ${nextDisabled}`} onClick={() => gotoPage(pageCount - 1)}>
        <a className="page-link"><ChevronDoubleRight /></a>
      </li>
      <li>
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
  const columns = specieInfo
    .fields
    .filter(column => column.hidden === 0)
    .map(column => { return { Header: column.label, accessor: column.name } })

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

const openDetailPage = (e) => {
  e.preventDefault()
  console.log(e)
}

export default IsoalteTable
