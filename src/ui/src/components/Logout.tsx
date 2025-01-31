import { Navigate } from 'react-router-dom';


const Logout = () => {
    localStorage.removeItem('spotifyToken');
    return <Navigate to="/" />;
  }

export default Logout;