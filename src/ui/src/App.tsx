// src/App.jsx
import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import Callback from './components/Callback';
import Logout from './components/Logout';

function App() {
  const [token, setToken] = useState(localStorage.getItem('spotifyToken'));

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route 
            path="/" 
            element={token ? <Navigate to="/dashboard" /> : <Login />} 
          />
          <Route 
            path="/callback" 
            element={<Callback setToken={setToken} />} 
          />
          <Route 
            path="/dashboard" 
            element={token ? <Dashboard token={token} setToken={setToken} /> : <Navigate to="/" />} 
          />
          <Route
            path='/logout'
            element={<Logout />}
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;