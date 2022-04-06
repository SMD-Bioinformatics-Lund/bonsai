import PropTypes from 'prop-types'
import { useState, useEffect } from 'react'
import "./Comment.css"
import { postCommentToSample } from '../api'

const CommentPanel = ({sampleId, comments}) => {
  const [sampleComments, setSampleComments] = useState(comments)
  const [commentText, setCommentText] = useState("")

  const postComment = async (e) => {
    e.preventDefault()
    if (commentText !== "") {
      const newComment = {
        username: "test",
        comment: commentText,
        displayed: true,
        createdAt: new Date().toISOString()
      }
      const newComments = [newComment, ...sampleComments] 
      console.log(newComments)
      setSampleComments(newComments)
      setCommentText("")
      document.getElementById("comment-field").value = ""
      // call API
      const response = await postCommentToSample(sampleId, newComment)
      setSampleComments(response)
    }
  }

  return (
    <div className="card">
      <div className="card-header">
      <h5 className="card-title">Comment</h5>
      </div>
      <div className="card-body">
      <form className="row">
          <textarea 
          id="comment-field"
          className="form-control" 
          rows="2"
          placeholder="Your comment..."
          onChange={(e) => {setCommentText(e.target.value)}}
          ></textarea>
          <button onClick={(e) => {postComment(e)}} className="btn btn-secondary">Add comment</button>
      </form>
      <hr></hr>
      <ul className="comment-list">
        {sampleComments.map((cmt) => {
            if (cmt.displayed) {
              return (
                <li className="comment" key={cmt.id}>
                  <Comment commentObj={cmt}/>
                </li>
              )
            }
        })}
      </ul>
      </div>
    </div>
  )
}


const Comment = ({commentObj}) => {
  const ctime = new Date(commentObj.createdAt);
  const cdate = `${ctime.getFullYear()}-${ctime.getMonth()}-${ctime.getDate()}`
  return (
      <div className="comment-body">
        <span className="float-right">
          <small className="text-muted">{cdate}</small>
        </span>
        <strong className="text-success">{commentObj.username}</strong>
        <p>{commentObj.comment}</p>
      </div>
  )
}

export default CommentPanel