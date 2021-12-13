export function getCellFormating(dataType) {
  // Select formating funtion depending on datatype
  let formatFunc;
  switch ( dataType ) {
    case 'pvl': 
      formatFunc = ({ cell: { value } }) => <PvlTyping value={value}/>;
      break;
    default:
      formatFunc = ({ cell: { value } }) => (<>{value}</>)
      break
  }
  return {Cell: formatFunc}
}


const PvlTyping = ({ value }) => {
  // Create PVL typing badge
  console.log(`---> ${value}`)
  let badgeColor
  switch (value) {
    case 'pos':
      badgeColor = 'bg-success';
      break;
    case 'neg':
      badgeColor = 'bg-warning';
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
