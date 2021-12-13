import React from "react";
import PropTypes from 'prop-types'

import { formatPvl, getMetadata, range } from '../../utils'
import { getCellFormating } from './Cell'
import { IndeterminateCheckbox, DefaultColumnFilter, GlobalFilter, parseFilterFunction } from './Filter'
import { useTable, usePagination, useSortBy, useFilters, useGlobalFilter, useRowSelect } from 'react-table'

//import Table from 'react-bootstrap/Table';
import { ArrowDownUp, SortUp, SortDown, ChevronDoubleRight, ChevronRight, ChevronLeft, ChevronDoubleLeft } from 'react-bootstrap-icons';
import 'bootstrap/dist/css/bootstrap.min.css';
import './Table.css';


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
                      { column.canSort ? (
                        <span className="ms-1">
                          {column.isSorted ? column.isSortedDesc ? <SortUp /> : <SortDown /> : <ArrowDownUp/>}
                        </span>
                      ) : '' }
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
        // will pass formating to rendering function
        ...getCellFormating(column.type),
        ...parseFilterFunction(column.filterType, column.filterParam),
        disableFilters: !column.filterable,
        disableSortBy: !column.sortable,
      } 
    })

  const data = sampleData.map(sample => {
    return {
      sampleId: sample.sample_id,
      specie: sample.top_brakken.top_species,
      mlstSt: sample.mlst.sequence_type,
      pvl: formatPvl(sample),
      date: sample.creation_date,
      qc: getMetadata(sample, 'QC'),
      location: getMetadata(sample, 'location'),
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
