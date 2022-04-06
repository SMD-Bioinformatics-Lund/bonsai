export function getCellFormating(dataType) {
  // Select formating funtion depending on datatype
  let formatFunc;
  switch ( dataType ) {
    case 'sampleId': 
      formatFunc = (props) => <SampleId props={props}/>;
      break;
    case 'pvl': 
      formatFunc = ({ cell: { value } }) => <PvlTyping value={value}/>;
      break;
    case 'mlstSt': 
      formatFunc = ({ cell: { value } }) => <MlstTyping value={value}/>;
      break;
    default:
      formatFunc = ({ cell: { value } }) => (<>{value}</>)
      break
  }
  return {Cell: formatFunc}
}

const SampleId = ({ props }) => {
  // Create PVL typing badge
  return (
    <a 
      href="#" 
      className="link-success"
      onClick={props.hasOwnProperty("onClick") ? () => {props.onClick(props.value, props.row.id)} : ''}
    >{ props.value }</a>
  );
}

const PvlTyping = ({ value }) => {
  // Create PVL typing badge
  let badgeColor
  switch (value) {
    case 'pos':
      badgeColor = 'bg-success';
      break;
    case 'neg':
      badgeColor = 'bg-danger';
      break;
    case 'pos/neg':
      badgeColor = 'bg-warning';
      break;
    case 'neg/pos':
      badgeColor = 'bg-warning';
      break;
    default:
      badgeColor = 'bg-secondary'
  }
  return (<span className={`badge ${badgeColor}`}>{value}</span>);
}

const MlstTyping = ({ value }) => {
  // Create PVL typing badge
  return (
    <span className="badge bg-secondary">{value}</span>
  );
}
