import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authTokenSlice';
import serverIPReducer from "./serverInfoTokenSlice"
const store = configureStore({
  reducer: {
    authToken: authReducer,
    serverIP: serverIPReducer
  },
});

export default store;
