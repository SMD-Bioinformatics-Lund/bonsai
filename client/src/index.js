import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { Provider } from 'react-redux';
import store from './store';
import 'bootstrap/dist/css/bootstrap.min.css';
import "@popperjs/core"
import "bootstrap"

//    <React.StrictMode>
//      
//    </React.StrictMode>

                //<Route path=":groupId" element={<Samples/>} />
ReactDOM
  .createRoot(document.getElementById('root'))
  .render(
    <Provider store={store}>
      <App/>
    </Provider>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
