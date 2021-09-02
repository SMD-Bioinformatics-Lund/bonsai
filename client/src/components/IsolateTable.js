import PropTypes from 'prop-types'

import Button from './Button'
import Select from './Select'
import { formatPvl, getMetadata } from '../utils'

const IsoalteTable = ({specieInfo, sampleData}) => {
  return (
    <div className="table-container">
      <ButtonRow/>
      <Table columnSpec={specieInfo.fields} sampleData={sampleData}/>
      <TableFooter/>
    </div>
  )
}

const ButtonRow = () => {
  const numSelected = 1
  const numIsolates = 100

  return (
    <div>
      <Button text="Generate tree"/>
      <Button text="Clear selection"/>
      <Button text="Select all"/>
      <Button text="Filter by date"/>
      <Button text="Columns"/>
      <span>{numSelected} of {numIsolates} isolates selected</span>
    </div>
  )
}

const Table = ({columnSpec, sampleData}) => {
  // remove colums
  const columns = columnSpec
    .filter((elem) => {return elem.hidden === 0})
    .map((elem) => {return elem.label})

  return (
    <table>
      <TableHead columns={columns}/>
      <tbody>
        { sampleData.map((row) => (<TableRow rowData={row} metaFields={columnSpec}/>)) }
      </tbody>
    </table>
  )
}

Table.propTypes = {
  columnSpec: PropTypes.array.isRequired,
}

const TableHead = ({columns}) => {
  const colNames = ['Sample ID', 'Species', 'MLST', 'PVL', 'Added', ...columns]

  return (
    <thead>
      <tr>
        {colNames.map((colName) => (<th>{colName}</th>) )}
      </tr>
    </thead>
  )
}

TableHead.defaultProps = {
  columns: [],
}

TableHead.propTypes = {
  columns: PropTypes.array,
}

const openDetailPage = (e) => {
  e.preventDefault()
  console.log(e)
}

const TableRow = ({rowData, metaFields}) => {
  // get pvl result and associate it with the right css class
  const pvlResult = formatPvl(rowData)
  let pvlClassName = ''
  if (pvlResult === 'pos') {
    pvlClassName = 'pos'
  } else if (pvlResult === 'neg') {
    pvlClassName = 'neg'
  }

  return (
    <tr>
      <td><a onClick={(e) => {openDetailPage(e)}} href='#'>{rowData.sample_id}</a></td> 
      <td>{rowData.top_brakken.top_species}</td>
      <td>{rowData.mlst.sequence_type}</td>
      <td className={pvlClassName}>{pvlResult}</td>
      <td>{rowData.creation_date}</td>
      {metaFields.map((field) => (<td>{getMetadata(rowData, field.name)}</td>))}
    </tr>
  )
}

function onChangeFunc(e) { alert(e) }

const TableFooter = () => {
  const speciesData = [
    {label: 'Species', value: 'species', selected: true},
    {label: 'Staphylococcus aureus', value: 'saureus', selected: false},
    {label: 'Staphylococcus aureus ?', value: 'q-saureus', selected: false},
  ]

  return (
    <div>
      <table>
        <tfoot>
          <td>
            <th><input type="text" placeholder="Search sample ID" /></th>
            <th>
              <Select 
              classNames='fool bar'
              onChange={(e) => onChangeFunc(e)}
              options={speciesData}/>
            </th>
          </td>
        </tfoot>
      </table>
    </div>
  )
}

export default IsoalteTable
