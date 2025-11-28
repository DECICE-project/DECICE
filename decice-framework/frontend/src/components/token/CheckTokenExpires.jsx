import { useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSelector, useDispatch } from "react-redux";
import { changeAuthToken } from "../../redux/authTokenSlice";

const decodeToken = (token) => {
    try {
      const payload = token.split('.')[1]; // Get the payload part of the token
      const decodedPayload = atob(payload.replace(/-/g, '+').replace(/_/g, '/')); // Decode from Base64URL
      return JSON.parse(decodedPayload); // Parse the JSON string
    } catch (error) {
      console.error("Invalid token", error);
      return null;
    }
  };


const useAuthCheck = (token) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const serverIP = useSelector((state) => state.serverIP.value);
  const refreshInProgressRef = useRef(false);

  const logOut = useCallback(() => {
    localStorage.removeItem("access_token");
    dispatch(changeAuthToken(null));
    navigate("/signin");
  }, [dispatch, navigate]);

  useEffect(() => {
    if (!token || !serverIP) return;

    const decodedToken = decodeToken(token);
    if (!decodedToken || !decodedToken.exp) {
      console.error("Invalid token or missing expiration");
      logOut();
      return;
    }

    refreshInProgressRef.current = false;

    const expirationTime = decodedToken.exp * 1000; // Convert to milliseconds
    const issuedAt = decodedToken.iat ? decodedToken.iat * 1000 : Date.now();
    const tokenLifetime = Math.max(expirationTime - issuedAt, 0);
    const fallbackThreshold = expirationTime - 60000; // 1 minute before expiry
    let refreshThresholdTime = tokenLifetime > 0
      ? expirationTime - tokenLifetime * 0.1
      : fallbackThreshold;
    refreshThresholdTime = Math.min(refreshThresholdTime, expirationTime - 1000);
    refreshThresholdTime = Math.max(refreshThresholdTime, issuedAt + 1000);

    const baseUrl = serverIP.startsWith('http') ? serverIP : `http://${serverIP}`;

    const refreshToken = async () => {
      if (refreshInProgressRef.current) return;
      refreshInProgressRef.current = true;
      try {
        const response = await fetch(`${baseUrl}/v1/user/me/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          Accept: 'application/json',
        },
        body: JSON.stringify({}),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            logOut();
            return;
          }
          throw new Error(`Failed to refresh token (${response.status})`);
        }

        const data = await response.json();
        const newToken = data?.token?.access_token;
        if (!newToken) {
          throw new Error('Refresh response did not include a new access token');
        }

        localStorage.setItem('access_token', newToken);
        dispatch(changeAuthToken(newToken));
      } catch (error) {
        console.error('Token refresh failed:', error);
      } finally {
        refreshInProgressRef.current = false;
      }
    };

    const checkTokenExpiration = () => {
      const currentTime = Date.now();
      if (currentTime >= expirationTime) {
        logOut(); // Redirect to the sign-in page
        return;
      }
      if (currentTime >= refreshThresholdTime && !refreshInProgressRef.current) {
        refreshToken();
      }
    };

    // Set up a timer to check every 10 seconds
    const intervalId = setInterval(checkTokenExpiration, 10000);

    // Check once on component mount
    checkTokenExpiration();

    return () => clearInterval(intervalId); // Cleanup on component unmount
  }, [token, serverIP, logOut, dispatch]);
};




const App = () => {
  const token = useSelector((state) => state.authToken.value);
  useAuthCheck(token); // Call the hook to check token expiration

  return null;
};

export default App;
