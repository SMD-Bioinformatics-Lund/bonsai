import {React, useState} from 'react'
import { useGetCurrentUserQuery, useLoginMutation } from '../services/mimer'
import { setCurrentUser } from '../reducers/user';
import { useNavigate } from 'react-router-dom'
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useDispatch } from 'react-redux';

export const Login = () => {
  const [inputs, setInputs] = useState({})
  const navigate = useNavigate()
  const dispatch = useDispatch()

  const [login, loginResult] = useLoginMutation()

  const handleInputChange = (event) => {
    const name = event.target.name
    const value = event.target.value 
    setInputs(values => ({...values, [name]: value}))
  }

  return (
    <div className='card' style={{width: '80%'}}>
      <div className='card-body'>
        <h1 className='card-title'>BaktAn</h1>
        <h2 className='card-subtitle mb-2 text-muted'>Annotate, Analyze, Act!</h2>
        <p className='card-text'>Please login to view your samples</p>
        <hr />
        <form>
          <div className='mb-3'>
            <label htmlFor="username-input" className="form-label">User name</label>
            <input name="username" type="text" onChange={handleInputChange} className="form-control" id="username-input" placeholder="Your username"></input>
          </div>
          <div className='mb-3'>
            <label htmlFor="password-input" className="form-label">Password</label>
            <input name="password" type="password" onChange={handleInputChange} className="form-control" id="password-input" placeholder="Password" />
          </div>
          <button className="btn btn-primary" onClick={async (event) => {
            event.preventDefault();
            try {
              const result = await login(inputs).unwrap()
            } catch (err) {
              toast.error(err.data.detail, {
                position: 'top-center',
                autoClose: 5000,
                hideProgressBar: false,
                closeOnClick: true,
                pauseOnHover: true,
              })
            }
            navigate('/')
          }}>
            Login
          </button>
        </form>
        <ToastContainer/>
      </div>
    </div>
  )
}
