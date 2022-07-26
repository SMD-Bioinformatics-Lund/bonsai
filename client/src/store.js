//import { createStore, applyMiddleware } from 'redux';
import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/dist/query";
import { authSlice } from "./reducers/auth";
import userSlice from "./reducers/user";
import { mimerApi } from "./services/mimer";

const store = configureStore({
  reducer: {
    // Add the generated reducer as a specific top-level slice
    [mimerApi.reducerPath]: mimerApi.reducer,
    [authSlice.name]: authSlice.reducer,
    [userSlice.name]: userSlice.reducer,
  },
  // add api middleware to enable caching, invalidation and polling etc
  middleware: (getDefaultMiddleware) => getDefaultMiddleware().concat(mimerApi.middleware)
 })

 setupListeners(store.dispatch)

 export default store