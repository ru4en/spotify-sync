import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, APIC, ID3NoHeaderError
import dataclasses

app = FastAPI()

DATA_DIR = os.getenv("DATA_DIR", "data")

@dataclasses.dataclass
class Track:
    name: str
    artist: str
    album: str
    image: str
    url: str

    def __str__(self):
        return f"{self.name} by {self.artist} from {self.album}"

@dataclasses.dataclass
class Playlist:
    name: str
    tracks: list[Track]

    def __str__(self):
        return f"{self.name} with {len(self.tracks)} tracks"

    def get_tracks(self):
        return self.tracks


class YouTubeDownloader:
    def __init__(self, data_dir, websockets=[]):
        self.data_dir = data_dir
        self.playlist_dir = os.path.join(os.getcwd(), 'playlists')
        self.playlists = []
        self.websockets = websockets
        assert os.path.exists(data_dir), f"{data_dir} does not exist"
        self.index()

    def index(self):
        for playlist in os.listdir(self.data_dir):
            playlist_dir = os.path.join(self.data_dir, playlist)
            if not os.path.isdir(playlist_dir) or playlist == "liked_songs":
                continue  
            tracks = []
            try:
                print(f"Indexing: {playlist}")
                tracks_json = json.load(open(os.path.join(playlist_dir, 'tracks.json')))
                for track in tracks_json['items']:
                    track_name = track['track']['name']
                    track_artist = track['track']['artists'][0]['name']
                    track_album = track['track']['album']['name']
                    track_image = os.path.join(playlist_dir, track_name, 'image.jpg')
                    track_url = track['track']['external_urls']['spotify']
                    tracks.append(Track(track_name, track_artist, track_album, track_image, track_url))
            except Exception as e:
                print(f"Error indexing {playlist}: {e}")
                continue
            self.playlists.append(Playlist(playlist, tracks))

    async def downloadAll(self):
        for playlist in self.playlists:
            playlist_dir = f"{self.playlist_dir}/{playlist.name}"
            os.makedirs(playlist_dir, exist_ok=True)

            for track in playlist.get_tracks():
                track_path = f"{playlist_dir}/{track.name}.mp3"
                if not os.path.exists(track_path):
                    track.url = await self.searchTrack(track)  # Ensure searchTrack is an async method
                    try:
                        await self.downloadTrack(track, playlist.name)  # Ensure downloadTrack is async
                        await self.send_progress(track, playlist.name, "Downloaded")
                        print(f"Downloaded: {track.name}")
                    except Exception as e:
                        await self.send_progress(track, playlist.name, "Failed")
                        print(f"Error downloading {track}: {e}")
                else:
                    await self.send_progress(track, playlist.name, "Already Downloaded")
                    print(f"Already Downloaded: {track.name}")
                await asyncio.sleep(1)

    async def send_progress(self, track, playlist_name, status, progress=0):
    # This function is responsible for sending the progress update to all WebSocket connections
        for websocket in self.websockets:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:  # Check if the connection is open
                    track_data = {
                        "title": track.name,
                        "artist": track.artist,
                        "url": track.url
                    }
                    await websocket.send_json(
                        {
                            "track": track_data,
                            "playlist": playlist_name,
                            "status": status,
                            "progress": progress
                        }
                    )
            except Exception as e:
                print(f"Error sending progress to websocket: {e}")

        
    async def searchTrack(self, track):
        ydl_opts = {
            'default_search': 'ytsearch',
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"{track.artist} {track.name}", download=False)
                return info['entries'][0]['webpage_url']
            except Exception as e:
                print(f"Error searching {track}: {e}")
                return None

    async def downloadTrack(self, track, playlist_name):
        os.makedirs(f"{self.playlist_dir}/{playlist_name}", exist_ok=True)
        dest = f"{self.playlist_dir}/{playlist_name}/{track.name}.%(ext)s"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': dest,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'progress_hooks': [self.progress_hook(track, playlist_name)]
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.add_default_info_extractors()
                ydl.download([track.url])
        except Exception as e:
            print(f"Error downloading {track}: {e}")
        self.setTrackMetadata(track, playlist_name)

    def progress_hook(self, track, playlist_name):
        # This hook will be called during the download progress
        def hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 1)  # Prevent division by zero
                progress = (downloaded / total) * 100
                print(f"Progress: {progress:.2f}%")
                asyncio.create_task(self.send_progress(track, playlist_name, "Downloading", progress))
        return hook

    def setTrackMetadata(self, track, playlist_name):
        file_path = f"{self.playlist_dir}/{playlist_name}/{track.name}.mp3"
        try:
            audio = MP3(file_path, ID3=ID3)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()

        # Add album cover image
        with open(track.image, 'rb') as album_art:
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=album_art.read()))
        # Add title, album, artist
        audio.tags.add(TIT2(encoding=1, text=track.name))
        audio.tags.add(TALB(encoding=1, text=track.album))
        audio.tags.add(TPE1(encoding=1, text=track.artist))
        audio.save(v2_version=3)


# WebSocket endpoint to track download progress
@app.websocket("/ws/download")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    downloader = YouTubeDownloader(DATA_DIR, websocket)
    await downloader.downloadAll()
    await websocket.close()


# HTTP endpoint to start the download
@app.get("/download")
async def download_all():
    return {"message": "Download started."}
