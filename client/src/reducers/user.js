import { createSlice } from "@reduxjs/toolkit";
import authSlice from "./auth";

export const userSlice = createSlice({
  name: 'user',
  initialState: { user: null },
  reducers: {
    setCurrentUser: (state, action) => state.user = action.payload,
    resetCurrentUser: (state) => state.user = null
  }
})

export const { setCurrentUser } = authSlice.actions

export default userSlice