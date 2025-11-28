import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  value: localStorage.getItem('access_token') || '',
};

const authSlice = createSlice({
  name: 'authToken',
  initialState,
  reducers: {
    changeAuthToken: (state, action) => {
      state.value = action.payload;
    },
  },
});

export const { changeAuthToken } = authSlice.actions;
export default authSlice.reducer;
