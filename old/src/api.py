import os
import json
import logging
import time
import asyncio
import urllib.request
from typing import List
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, WebSocket, BackgroundTasks, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from spotipy.oauth2 import SpotifyOAuth
from spotify import get_spotify_client, OAuthHandler
from youtube import YouTubeDownloader

app = FastAPI()
app.mount("/static", StaticFiles(directory="ui"), name="static")

active_connections: List[WebSocket] = []


# Environment variables with default values and error handling
HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("PORT", 8080))
PROTOCOL = os.getenv("PROTOCOL", "http")
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://spotify-sync.ditto.rlab.uk/callback')
DATA_DIR = os.getenv("DATA_DIR", "data")
PLAYLISTS_DIR = os.getenv("PLAYLISTS_DIR", "playlists")

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set in environment variables.")

# Spotify OAuth setup
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="playlist-read-private user-library-read"
)


@app.get("/")
def read_root():
    return FileResponse("ui/index.html")


@app.get("/auth")
def auth_spotify():
    """Start Spotify authentication."""
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@app.get("/callback")
def callback(code: str):
    """Finish Spotify authentication."""
    token_info = sp_oauth.get_access_token(code)
    return RedirectResponse("/")


@app.get("/playlists")
def get_playlists():
    """Get the list of playlists and their tracks."""
    sp = get_spotify_client()
    data = []
    user_playlists = sp.current_user_playlists()
    for playlist in user_playlists["items"]:
        tracks = sp.playlist_tracks(playlist['id'])
        data.append({
            "name": playlist['name'],
            "image": playlist['images'][0]['url'],
            "tracks": [
                {
                    "id": track['track']['id'],
                    "url": track['track']['external_urls']['spotify'],
                    "image": track['track']['album']['images'][0]['url'],
                    "name": track['track']['name'],
                    "artist": track['track']['artists'][0]['name'],
                    "album": track['track']['album']['name'],
                    "isSynced": os.path.exists(f"{DATA_DIR}/{playlist['name']}/{track['track']['name']}"),
                    "isDownloaded": os.path.exists(f"{PLAYLISTS_DIR}/{playlist['name']}/{track['track']['name']}.mp3")
                }
                for track in tracks['items']
            ]
        })
    return data


def save_track_data(track, track_dir, sp):
    """Save track metadata, features, and album art."""
    track_info_file = f"{track_dir}/info.json"
    if not os.path.exists(track_info_file):
        song_info = sp.track(track['track']['id'])
        with open(track_info_file, 'w') as f:
            json.dump(song_info, f)

    track_features_file = f"{track_dir}/features.json"
    if not os.path.exists(track_features_file):
        features = sp.audio_features(track['track']['id'])
        with open(track_features_file, 'w') as f:
            json.dump(features, f)

    track_image_file = f"{track_dir}/image.jpg"
    if not os.path.exists(track_image_file):
        image_url = track['track']['album']['images'][0]['url']
        with open(track_image_file, 'wb') as image_f:
            image_f.write(urllib.request.urlopen(image_url).read())

def process_playlist(sp, playlist, playlist_dir):
    """Process playlist tracks and save them locally."""
    tracks = sp.playlist_tracks(playlist['id'])
    with open(f"{playlist_dir}/tracks.json", 'w') as playlist_file:
        json.dump(tracks, playlist_file)

    for track in tracks['items']:
        track_itm = track.get('track', {}) if track else None
        track_name = track_itm.get('name') if track_itm else None
        if not track_name:
            logger.info(f"Skipping track with no name.")
            continue

        track_dir = f"{playlist_dir}/{track_name}"
        if os.path.exists(track_dir):
            logger.info(f"Skipping track {track_name}, already processed.")
            continue

        os.makedirs(track_dir, exist_ok=True)
        logger.info(f"Processing track {track_name}...")
        save_track_data(track, track_dir, sp)


@app.get("/sync")
def sync_spotify_data():
    """Synchronize playlists and saved songs from Spotify."""
    try:
        sp = get_spotify_client()
        
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

        # Process playlists
        user_playlists = sp.current_user_playlists()
        for playlist in user_playlists["items"]:
            playlist_name = playlist['name']
            playlist_dir = f"{DATA_DIR}/{playlist_name}"

            if os.path.exists(playlist_dir):
                logger.info(f"Skipping playlist {playlist_name}, already processed.")
                continue

            os.makedirs(playlist_dir, exist_ok=True)
            logger.info(f"Processing playlist {playlist_name}...")
            process_playlist(sp, playlist, playlist_dir)
            time.sleep(1)

        # Process liked songs
        liked_songs_dir = f"{DATA_DIR}/liked_songs"
        os.makedirs(liked_songs_dir, exist_ok=True)
        
        liked_songs = sp.current_user_saved_tracks()
        for song in liked_songs['items']:
            track_name = song['track']['name']
            track_dir = f"{liked_songs_dir}/{track_name}"

            if os.path.exists(track_dir):
                logger.info(f"Skipping liked song {track_name}, already processed.")
                continue

            os.makedirs(track_dir, exist_ok=True)
            logger.info(f"Processing liked song {track_name}...")
            save_track_data(song, track_dir, sp)
            time.sleep(1)

        logger.info("Sync completed successfully.")
        return {"message": "Sync completed successfully."}

    except Exception as e:
        logger.error(f"Error during Spotify sync: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during Spotify sync: {str(e)}")


@app.get("/download/all")
async def download_all(background_tasks: BackgroundTasks):
    """Start downloading all tracks from YouTube based on local data."""
    try:
        downloader = YouTubeDownloader(DATA_DIR, active_connections)
        background_tasks.add_task(downloader.downloadAll)
        return {"message": "Downloading started."}
    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error during download: {str(e)}")
    
@app.websocket("/ws/download")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "close":
                await websocket.close()
                break
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        await websocket.close()

@app.post("/download/{playlist_name}")
async def download_playlist(playlist_name: str):
    try:
        downloader = YouTubeDownloader(Config.DATA_DIR)
        asyncio.create_task(downloader.start_download([playlist_name]))
        return {"message": f"Download started for playlist: {playlist_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/status")
async def get_download_status():
    downloader = YouTubeDownloader(Config.DATA_DIR)
    return {
        "playlists": [
            {
                "name": playlist.name,
                "progress": playlist.get_progress(),
                "tracks": [track.to_dict() for track in playlist.tracks]
            }
            for playlist in downloader.playlists
        ]
    }