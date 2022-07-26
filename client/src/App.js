import Navbar from './components/Navbar';
import { useSelector } from 'react-redux';
import { useEffect } from 'react';
import { selectToken } from './reducers/auth';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Samples from './routes/SamplesPage'
import Groups from './routes/GroupsPage'
import { Login } from './routes/Login';
import PrivateRoute from './routes/PrivateRoute'
import { ErrorPage } from './routes/ErrorPage';
import { SamplePage } from './routes/SamplePage'

function App() {
  // setup listener for changes in token states
  // and update token stored in localStorage
  const token = useSelector(selectToken)
  useEffect(() => {
    localStorage.setItem("token", token)
  }, [token])
  return (
    <BrowserRouter>
      <Navbar/>
      <Routes>
        <Route path="/login" element={<Login/>} />
        <Route path="/" element={<PrivateRoute/>}>
          <Route path="/" element={<Groups />}/>
          <Route path="/groups/:groupId" element={<Samples/>} />
          <Route path="/groups/:groupId/:sampleId" element={<SamplePage/>}/>
          <Route path="/locations" />
          <Route path="/locations/:locationId" />
        </Route>
        <Route path="*" element={<ErrorPage/>} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
