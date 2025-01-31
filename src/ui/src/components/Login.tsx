// src/components/Login.jsx

const Login = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto p-4 text-center dark:text-white dark:bg-gray-800
      bg-opacity-50 rounded-lg shadow-lg 
      ">
      <h1>Spotify Playlist Manager</h1>
      <a
        className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded mt-4 inline-block"
        href="https://accounts.spotify.com/authorize?response_type=code&client_id=379b346063b24eb29cbd5464446d87ae&redirect_uri=http://localhost/callback&scope=playlist-read-collaborative%20playlist-modify-private%20playlist-read-private%20playlist-modify-public%20user-read-private%20user-read-email%20user-read-playback-state%20user-modify-playback-state%20user-read-currently-playing%20user-library-modify%20user-library-read%20user-read-playback-position%20user-read-recently-played%20user-top-read%20user-follow-read%20user-follow-modify"
      >
        Login with Spotify
      </a>

      <p className="text-sm mt-4 text-gray-400">
        This app requires a Spotify account to manage playlists.
      </p>
      </div>
      </div>
  );
}

export default Login;