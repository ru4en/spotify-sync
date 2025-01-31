import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { SpotifyAuthResponse } from './Types';

interface CallbackProps {
  setToken: (token: string) => void;
}

const Callback: React.FC<CallbackProps> = ({ setToken }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async (): Promise<void> => {
      const code = searchParams.get('code');
      
      if (!code) {
        setError('No authorization code found in URL');
        return;
      }

      try {
        // Make sure this matches your FastAPI backend URL
        const response = await fetch(`http://localhost/api/callback?${new URLSearchParams({ code: code })}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });
          
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
          
        const data: SpotifyAuthResponse = await response.json();

        if (!data.token.access_token) {
          throw new Error('No access token received from server');
        }

        // Store token and redirect
        localStorage.setItem('spotifyToken', data.token.access_token);
        setToken(data.token.access_token);
        console.log('Successfully authenticated with Spotify' + data.token.access_token);
        navigate('/dashboard');
        
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
        setError(errorMessage);
        console.error('Authentication error:', errorMessage);
        
        // Wait a bit before redirecting on error
        setTimeout(() => {
          navigate('/');
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, setToken]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      {error ? (
        <div className="text-red-500 text-center p-4">
          <h2 className="text-xl font-bold mb-2">Authentication Error</h2>
          <p>{error}</p>
          <p className="mt-2 text-sm">Redirecting to login...</p>
        </div>
      ) : (
        <div className="text-center">
          <h2 className="text-xl font-bold mb-4">Authenticating with Spotify...</h2>
          <div className="w-12 h-12 border-4 border-green-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
        </div>
      )}
    </div>
  );
};

export default Callback;