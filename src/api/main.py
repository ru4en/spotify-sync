from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional
import requests
import uvicorn
import os
import dotenv

dotenv.load_dotenv()

# Configuration
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost/callback")

app = FastAPI()

def get_spotify_auth_url():
    scope = [
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-read-private",
        "playlist-modify-public",
        "user-read-private",
        "user-read-email",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-library-modify",
        "user-library-read",
        "user-read-playback-position",
        "user-read-recently-played",
        "user-top-read",
        "user-follow-read",
        "user-follow-modify",
    ]
    return f"https://accounts.spotify.com/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={' '.join(scope)}"

def get_token_from_code(auth_code: str) -> dict:
    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
            },
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Token acquisition failed: {str(e)}")

def refresh_access_token(refresh_token: str) -> Optional[dict]:
    try:
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

@app.get("/ping")
async def ping():
    return {"ping": "pong"}

@app.get("/")
async def auth():
    auth_url = get_spotify_auth_url()
    return HTMLResponse(content=f'<a href="{auth_url}">Authorize with Spotify</a>')

@app.get("/callback")
async def callback(code: str):
    try:
        token_data = get_token_from_code(code)
        return {"token": token_data}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/playlists")
async def get_playlists(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me/playlists",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch playlists: {str(e)}")

@app.get("/playlist/{playlist_id}")
async def get_playlist(request: Request, playlist_id: str):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch playlist: {str(e)}")


@app.get("/me")
async def get_user_profile(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch user profile: {str(e)}")


@app.get("/download/playlist/{playlist_id}")
async def download_playlist(request: Request, playlist_id: str):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch playlist: {str(e)}")

    playlist_tracks = response.json().get("tracks", {}).get("items", [])
    for track in playlist_tracks:
        track_name = track.get("track", {}).get("name")
        track_artist = track.get("track", {}).get("artists", [{}])[0].get("name")
        print(f"Downloading {track_name} by {track_artist}")

    return {"playlist": playlist_tracks}

@app.get("/download/track/{track_id}")
async def download_track(request: Request, track_id: str):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            f"https://api.spotify.com/v1/tracks/{track_id}",
            headers={"Authorization": token},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch track: {str(e)}")

    track_name = response.json().get("name")
    track_artist = response.json().get("artists", [{}])[0].get("name")
    print(f"Downloading {track_name} by {track_artist}")

    return {"track": response.json()}


@app.get("/search/tracks")
async def search_tracks(request: Request, query: str):
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Authorization token missing")
    try:
        response = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": token},
            params={"q": query, "type": "track"},
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to search tracks: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000, debug=True)