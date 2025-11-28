import React from 'react'
import ReactDOM from 'react-dom/client'
import {NextUIProvider} from '@nextui-org/react'
import './index.css'
import ThemeProvider from './components/dashboard/ThemeContext';
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import HomePage from "./components/homepage/page"
import Dashboard from "./components/dashboard/App";
import Signin from "./pages/Signin"
import './App.css'
import { ToastContainer} from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import store from './redux/store'
import { Provider } from 'react-redux'
const router = createBrowserRouter([
  {
    path: "/",
    element:<HomePage/>,
    errorElement:<p>merhaba</p>
  },
  {
    path: "/dashboard",
    element: <Dashboard/>,
  },
  {
    path: "/signin",
    element: <Signin/>,
  },
]);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
      <Provider store={store}>
    <NextUIProvider>
    <ThemeProvider>
    <RouterProvider router={router} />
      </ThemeProvider>
      <ToastContainer
position="bottom-left"
autoClose={5000}
hideProgressBar={false}
newestOnTop={false}
closeOnClick
rtl={false}
pauseOnFocusLoss
draggable
pauseOnHover
/>
    </NextUIProvider>
    </Provider>
  </React.StrictMode>,
)
