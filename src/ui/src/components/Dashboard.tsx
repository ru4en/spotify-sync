import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Music, LogOut, Loader2, AlertCircle, Search } from 'lucide-react';
import { Playlist, UserProfile } from './Types';
import CoverShuffle from './CoverShuffle';

interface DashboardProps {
  token: string;
  setToken: (token: string | null) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ token, setToken }) => {
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  // const [setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<[]>([]);
  const [selectedPlaylist, setSelectedPlaylist] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSetSelectedPlaylist = (playlistId: string) => {
    setSelectedPlaylist(playlistId);
    CoverShuffle({ playlistId });
  };

  const fetchUserData = async (playlistId?: string, trackId?: string, query?: string) => {
    setLoading(true);
    const endpoints = [
      'http://localhost/api/me',
      'http://localhost/api/playlists',
      query ? `http://localhost/api/search/tracks?query=${query}` : null,
      playlistId ? `http://localhost/api/download/playlist/${playlistId}` : null,
      trackId ? `http://localhost/api/download/track/${trackId}` : null
    ].filter(Boolean) as string[];

    try {
      const responses = await Promise.all(
        endpoints.map(endpoint =>
          fetch(endpoint, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
        )
      );

      const data = await Promise.all(responses.map(response => {
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }
        return response.json();
      }));

      const [
        profileData,
        playlistsData,
        searchResults,
        ...otherData
      ] = data;
      
      setUserProfile(profileData);
      setPlaylists(playlistsData.items || []);
      setSearchResults(searchResults?.tracks.items || []);
      
      if (playlistId && otherData[0]) {
        setPlaylists(otherData[0].items || []);
      }
      
      // if (trackId && otherData[1]) {
      //   setTracks(otherData[1].tracks || []);
      // }

    } catch (error) {
      console.error('Failed to fetch user data:', error);
      setError(error instanceof Error ? error.message : 'Failed to fetch data');
      if (error instanceof Error && error.message.includes('401')) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserData();
  }, [token]);

  const handlePlaylistSelect = async (playlistId: string) => {
    handleSetSelectedPlaylist(playlistId);
    await fetchUserData(playlistId);
  };

  // const handleTrackDownload = async (trackId: string) => {
  //   await fetchUserData(undefined, trackId);
  // };

  const handleSearch = async (query: string) => {
    if (!query.trim()) return;
    await fetchUserData(undefined, undefined, query);
  };

  const handleLogout = () => {
    localStorage.removeItem('spotifyToken');
    setToken(null);
    navigate('/');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-green-500 mx-auto" />
          <p className="mt-4 text-gray-300">Loading your music...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
          <p className="mt-4 text-red-400">Error: {error}</p>
          <button 
            onClick={() => fetchUserData()}
            className="mt-4 px-6 py-2 bg-red-500 hover:bg-red-600 rounded-full transition-colors duration-200"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  console.log('User Profile:', userProfile);
  console.log('Playlists:', playlists);
  console.log('Search Results:', searchResults.slice(0, 5));

  return (
    <div className="min-h-screen bg-[#090909] overflow-hidden">
      {/* Ambient Background Effects */}
      <div className="fixed inset-0">
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-purple-900/20 via-black to-blue-900/20" />
        <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] animate-[spin_60s_linear_infinite] opacity-30">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(120,119,198,0.3)_0,rgba(0,0,0,0)_100%)]" />
        </div>
      </div>

      {/* Header with Glassmorphism */}
      <header className="fixed top-0 w-full z-50 backdrop-blur-xl bg-black/20 border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 p-[2px] animate-glow">
                <div className="w-full h-full rounded-full bg-black flex items-center justify-center">
                  <a href="/" className="text-white font-bold text-lg">
                    <Music className="h-5 w-5 text-white" />
                  </a>
                </div>
              </div>
            </div>

            {/* Search Bar with Glassmorphism */}
            <div className="flex items-center space-x-6">
              <div className="relative group">
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
                  className="w-64 px-4 py-2 pl-10 rounded-xl bg-white/10 backdrop-blur-xl 
                           border border-white/10 text-white placeholder-white/50
                           focus:outline-none focus:ring-2 focus:ring-purple-500/50
                           transition-all duration-300"
                />
                <Search className="absolute left-3 top-2.5 h-5 w-5 text-white/50" />
              </div>

              {userProfile && (
                <div className="flex items-center space-x-4">
                  <img
                    src={userProfile.images?.[0]?.url || '/default-avatar.png'}
                    alt="Profile"
                    className="w-10 h-10 rounded-full border-2 border-purple-500/50"
                  />
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2 rounded-xl bg-white/10 backdrop-blur-xl
                             border border-white/10 text-white
                             hover:bg-white/20 transition-all duration-300
                             flex items-center space-x-2"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="pt-24 px-6 pb-12 relative">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Playlists Grid Cards */}
          {
            selectedPlaylist ? (
              <>
                <button
                  onClick={() => setSelectedPlaylist(null)}
                  className="px-8 py-4 rounded-xl bg-white/10 backdrop-blur-xl
                             border border-white/10 text-white
                             hover:bg-white/20 transition-all duration-300
                             flex items-center space-x-2"
                >
                  <span>Back to Playlists</span>
                </button>
                <CoverShuffle playlistId={selectedPlaylist} />
              </>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-8">
                {playlists.map((playlist, index) => (
                  <div
                    key={playlist.id}
                    className="group relative animate-slide-up"
                    style={{ animationDelay: `${index * 0.1}s` }}
                    onClick={() => handlePlaylistSelect(playlist.id)}
                  >
                    {/* Card with Glassmorphism */}
                    <div className="relative overflow-hidden rounded-2xl backdrop-blur-xl bg-white/5 
                                  border border-white/10 transition-all duration-500
                                  hover:scale-105 hover:bg-white/10 hover:border-purple-500/30
                                  cursor-pointer">
                      {/* Image Container */}
                      <div className="relative aspect-square">
                        <img
                          src={playlist.images?.[0]?.url || '/default-playlist.png'}
                          alt={playlist.name}
                          className="w-full h-full object-cover transition-all duration-500
                                  group-hover:brightness-110"
                        />
                        {/* Hover Overlay */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent 
                                      opacity-0 group-hover:opacity-100 transition-all duration-500
                                      flex items-center justify-center">
                          <button className="px-6 py-3 rounded-full bg-white/20 backdrop-blur-md
                                          border border-white/30 text-white duration-300
                                          transform translate-y-4 opacity-0
                                          group-hover:translate-y-0 group-hover:opacity-100
                                          transition-all duration-500 hover:bg-white/30">
                            Download
                          </button>
                        </div>
                      </div>

                      {/* Playlist Info */}
                      <div className="p-4 space-y-2">
                        <h3 className="font-semibold text-white truncate group-hover:text-purple-300
                                    transition-colors duration-300">
                          {playlist.name}
                        </h3>
                        <p className="text-sm text-white/60 flex items-center">
                          <Music className="h-4 w-4 mr-2 text-purple-400" />
                          {playlist.tracks.total} tracks
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )
          }
        </div>
      </main>
    </div>
  );
};

export default Dashboard;