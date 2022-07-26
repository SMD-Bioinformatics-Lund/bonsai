import { createSlice } from "@reduxjs/toolkit";
import { mimerApi } from "../services/mimer";

export const authSlice = createSlice({
  name: "auth",
  initialState: { token: localStorage.getItem("token") || "" },
  reducers: {
    logout: (state) => {
      state.token = ""
    }
  },
  extraReducers: (builder) => {
    // add login reducer from mimerApi
    // call login api and set token state to the result of api call
    builder
    .addMatcher(
      mimerApi.endpoints.login.matchFulfilled, 
      (state, action) => {
        state.token = action.payload.access_token
      }
    )
  }
})

export const { logout } = authSlice.actions

export default authSlice;

export const selectToken = (state) => state.auth.token