function pathBaseName(path) { return path.split('/').pop() }


const DetailedResult = ({selectedSample, displayDetailedResult, closeDetailedResultPanelFunc}) => {
  // display detailed result for a sample
  // define relevant data categories
  const dataTables = [
    {
      title: "Meta info",
      data: {
        Run: pathBaseName(selectedSample.run),
      },
    },
    {
      title: "Quality Control",
      data: {
        "Assembly Size": selectedSample.quast["Total Length"],
        "# Contigs": selectedSample.quast["Total Length"],
        N50: selectedSample.quast.N50,
        "GC %": selectedSample.quast["GC (%)"],
      },
    },
    {
      title: "Typing",
      data: {
        "MLST ST": selectedSample.mlst.sequence_type,
      },
    },
  ]

  const comment = selectedSample.metadata.hasOwnProperty("comment") ? selectedSample.metadata.comment : ''

  return (
    <div className="card" hidden={!displayDetailedResult}>
      <div className="card-header bg-success text-white position-relative">
        {`Sample id: ${selectedSample.sample_id}`}
        <button onClick={() => closeDetailedResultPanelFunc()} type="button" className="btn-close btn-close-white float-end" aria-label="Close"></button>
      </div>
      {dataTables.map( (tbl) => (
          <div className="card-body">
            <h5 className="card-title">{tbl.title}</h5>
            <table className="table">
              {Object.entries(tbl.data).map(([key, val]) => (
                <tr><th scope="row">{key}</th><td>{val}</td></tr>
              ))}
            </table>
          </div>
        ))
      }
      <div className="card-body">
        <h5 className="card-title">Comment</h5>
        <form className="row">
          <textarea 
            className="form-control" 
            rows="2"
            placeholder={
              selectedSample.metadata.hasOwnProperty("comment") ? 
              selectedSample.metadata.comment : ''
            }
          ></textarea>
          <button type="Submit" className="btn btn-secondary">Add comment</button>
        </form>
      </div>
    </div>
  );
};


export default DetailedResult
