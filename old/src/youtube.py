import os
import json
import asyncio
from typing import List, Optional, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, APIC, ID3NoHeaderError
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Environment configuration
class Config:
    DATA_DIR = os.getenv("DATA_DIR", "data")
    MAX_CONCURRENT_DOWNLOADS = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    DOWNLOAD_RETRY_ATTEMPTS = int(os.getenv("DOWNLOAD_RETRY_ATTEMPTS", "3"))
    DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))  # 5 minutes

class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Track:
    name: str
    artist: str
    album: str
    image: str
    url: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress: float = 0.0
    error: Optional[str] = None

    def to_dict(self):
        return {
            **asdict(self),
            "status": self.status.value
        }

@dataclass
class Playlist:
    name: str
    tracks: List[Track]
    download_status: Dict[str, DownloadStatus] = None

    def __post_init__(self):
        self.download_status = {}
        
    def get_progress(self):
        completed = sum(1 for track in self.tracks if track.status in 
                       [DownloadStatus.COMPLETED, DownloadStatus.SKIPPED])
        return (completed / len(self.tracks)) * 100 if self.tracks else 0

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

class YouTubeDownloader:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.playlist_dir = os.path.join(os.getcwd(), 'playlists')
        self.playlists: List[Playlist] = []
        self.download_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_DOWNLOADS)
        self._initialize_directories()
        self.index()

    def _initialize_directories(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.playlist_dir, exist_ok=True)

    def index(self):
        try:
            for playlist_name in os.listdir(self.data_dir):
                playlist_path = os.path.join(self.data_dir, playlist_name)
                if not os.path.isdir(playlist_path) or playlist_name == "liked_songs":
                    continue

                tracks = self._load_playlist_tracks(playlist_path, playlist_name)
                if tracks:
                    self.playlists.append(Playlist(playlist_name, tracks))
                    logger.info(f"Indexed playlist: {playlist_name} with {len(tracks)} tracks")
        except Exception as e:
            logger.error(f"Error during indexing: {e}")

    def _load_playlist_tracks(self, playlist_path: str, playlist_name: str) -> List[Track]:
        try:
            with open(os.path.join(playlist_path, 'tracks.json')) as f:
                tracks_data = json.load(f)
            
            return [
                Track(
                    name=track['track']['name'],
                    artist=track['track']['artists'][0]['name'],
                    album=track['track']['album']['name'],
                    image=os.path.join(playlist_path, track['track']['name'], 'image.jpg'),
                    url=track['track']['external_urls']['spotify']
                )
                for track in tracks_data['items']
            ]
        except Exception as e:
            logger.error(f"Error loading playlist {playlist_name}: {e}")
            return []

    async def process_download_queue(self):
        while True:
            try:
                playlist, track = await self.download_queue.get()
                await self._process_track(track, playlist.name)
                self.download_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing download queue: {e}")
                await asyncio.sleep(1)

    async def _process_track(self, track: Track, playlist_name: str):
        track_path = f"{self.playlist_dir}/{playlist_name}/{track.name}.mp3"
        
        if os.path.exists(track_path):
            track.status = DownloadStatus.SKIPPED
            await self._broadcast_progress(track, playlist_name)
            return

        for attempt in range(Config.DOWNLOAD_RETRY_ATTEMPTS):
            try:
                track.status = DownloadStatus.DOWNLOADING
                await self._broadcast_progress(track, playlist_name)
                
                if not track.url.startswith('http'):
                    track.url = await self._search_track(track)
                
                if track.url:
                    await self._download_track(track, playlist_name)
                    track.status = DownloadStatus.COMPLETED
                else:
                    raise Exception("No URL found for track")
                
                break
            except Exception as e:
                logger.error(f"Download attempt {attempt + 1} failed for {track.name}: {e}")
                track.error = str(e)
                track.status = DownloadStatus.FAILED if attempt == Config.DOWNLOAD_RETRY_ATTEMPTS - 1 else DownloadStatus.PENDING
                
            await self._broadcast_progress(track, playlist_name)
            if track.status == DownloadStatus.FAILED:
                break
            
            await asyncio.sleep(1)

    async def _search_track(self, track: Track) -> Optional[str]:
        try:
            loop = asyncio.get_event_loop()
            ydl_opts = {
                'default_search': 'ytsearch',
                'quiet': True,
                'extract_flat': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(
                    self.executor,
                    lambda: ydl.extract_info(f"{track.artist} {track.name}", download=False)
                )
                return info['entries'][0]['webpage_url']
        except Exception as e:
            logger.error(f"Error searching for track {track.name}: {e}")
            return None

    async def _download_track(self, track: Track, playlist_name: str):
        dest = f"{self.playlist_dir}/{playlist_name}/{track.name}.%(ext)s"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': dest,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'progress_hooks': [self._create_progress_hook(track, playlist_name)]
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._download_with_timeout,
            track,
            ydl_opts
        )

    def _download_with_timeout(self, track: Track, ydl_opts: dict):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([track.url])
        except Exception as e:
            logger.error(f"Error downloading {track.name}: {e}")
            raise

    def _create_progress_hook(self, track: Track, playlist_name: str):
        async def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                if total > 0:
                    track.progress = (downloaded / total) * 100
                    await self._broadcast_progress(track, playlist_name)

        return progress_hook

    async def _broadcast_progress(self, track: Track, playlist_name: str):
        await manager.broadcast({
            "track": track.to_dict(),
            "playlist": playlist_name,
            "status": track.status.value,
            "progress": track.progress
        })

    async def start_download(self, playlist_names: Optional[List[str]] = None):
        workers = [asyncio.create_task(self.process_download_queue()) 
                  for _ in range(Config.MAX_CONCURRENT_DOWNLOADS)]

        try:
            for playlist in self.playlists:
                if playlist_names and playlist.name not in playlist_names:
                    continue
                    
                for track in playlist.tracks:
                    await self.download_queue.put((playlist, track))

            await self.download_queue.join()
        finally:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
