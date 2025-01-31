
export interface UserProfile {
  images: { url: string }[];
  display_name: string;
  email: string;
}

export interface Playlist {
  id: string;
  name: string;
  images: { url: string }[];
  tracks: {
    total: number;
  };
}

export interface Track {
  id: string;
  name: string;
  artists: { name: string }[];
  coverUrl: string;
}

export interface SpotifyAuthResponse {
  token: {
    access_token: string;
    token_type: string;
    expires_in: number;
    refresh_token: string;
    scope: string;
  }
}
