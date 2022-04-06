import CommentPanel from './Comment';

function pathBaseName(path) { return path.split('/').pop() }


const DetailedResult = ({selectedSample, displayDetailedResult, closeDetailedResultPanelFunc}) => {
  // display detailed result for a sample
  // define relevant data categories
  const mlstResult = selectedSample.addTypingResult.filter(res => res.type === "mlst")
  const dataTables = [
    {
      title: "Meta info",
      data: {
        Run: selectedSample.runMetadata.run.run,
      },
    },
    {
      title: "Quality Control",
      data: {
        "Assembly Size": selectedSample.qc.assembly.total_length,
        "# Contigs": selectedSample.qc.assembly.n_contigs,
        N50: selectedSample.qc.assembly.n50,
        "GC %": selectedSample.qc.assembly.assebly_gc,
      },
    },
    {
      title: "Typing",
      data: {
        "MLST ST": mlstResult.length > 0 ?  mlstResult[0].sequenceType : "",
      },
    },
  ]

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
      <CommentPanel sampleId={selectedSample.sampleId} comments={selectedSample.comments}/>
    </div>
  );
};


export default DetailedResult
