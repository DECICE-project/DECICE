import { useState,useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux'
import { changeAuthToken } from '../../redux/authTokenSlice';
import { useNavigate } from "react-router-dom";
import {Modal, ModalContent, ModalHeader, ModalBody, ModalFooter, Button, useDisclosure} from "@nextui-org/react";

export default function SignIn() {
  const {isOpen, onOpen, onOpenChange} = useDisclosure();
  const serverIP = useSelector((state) => state.serverIP.value);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  const authToken = useSelector(state => state.authToken.value);
  const dispatch = useDispatch();
  const navigate = useNavigate();

useEffect(() => {
  if(authToken){
  navigate("/dashboard");}
}, [authToken])


  const handleSubmit = async (e) => {
    e.preventDefault();

    const requestOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'accept': 'application/json',
      },
      body: new URLSearchParams({
        'grant_type': 'password',
        'username': email,
        'password': password,
        'scope': '',
        'client_id': '',
        'client_secret': ''
      })
    };

    try {

      const response = await fetch(`http://${serverIP}/v1/token/`, requestOptions);
      if (!response.ok) {
        throw new Error('Login failed');
      }
      const data = await response.json();
      console.log('Access Token:', data.access_token); // Store this token as needed
      localStorage.setItem("access_token", data.access_token);

      dispatch(changeAuthToken(data.access_token));
    } catch (error) {
      setError('Login failed. Please check your credentials.');
      console.error('Error:', error);
    }
  };

  return (
    <>
      <div className="mb-10 dark:text-zinc-100">
        <h1 className="text-4xl font-bold ">Sign in to your account</h1>
      </div>
      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="space-y-4 ">
          <div>
            <label
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-zinc-100"
              htmlFor="email"
            >
              Username
            </label>
            <input
              id="email"
              name="email"
              className="form-input w-full py-2"
              type="text"
              placeholder="user"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label
              className="mb-1 block text-sm font-medium text-gray-700 dark:text-zinc-100"
              htmlFor="password"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              className="form-input w-full py-2"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        </div>
        {error && <p className="text-red-500 mt-4">{error}</p>}
        <div className="mt-6">
          <button className="btn w-full bg-gradient-to-t from-blue-600 to-blue-500 bg-[length:100%_100%] bg-[bottom] text-white shadow hover:bg-[length:100%_150%]">
            Sign In
          </button>
        </div>
      </form>
      {/* Bottom link */}
      <div className="mt-6 text-center">
      <>
      <Button  className="text-sm text-gray-700 underline hover:no-underline dark:text-zinc-100" variant='light' onPress={onOpen}>Forgot Password</Button>
      <Modal isOpen={isOpen} onOpenChange={onOpenChange}>
        <ModalContent>
          {(onClose) => (
            <>
              <ModalHeader className="flex flex-col gap-1">Info of Forgot Password</ModalHeader>
              <ModalBody>
                <p>
                Kindly get in touch with the decice service department to retrieve your password.
                </p>
                <p>
                You can reach them at this address: password.services@decice.eu
                </p>
              </ModalBody>
              <ModalFooter>
                <Button color="danger" variant="light" onPress={onClose}>
                  Close
                </Button>
              </ModalFooter>
            </>
          )}
        </ModalContent>
      </Modal>
    </>

      </div>

    </>
  );
}
