from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import http.server
import os
from dotenv import load_dotenv
import urllib.parse
import json
import argparse
import uvicorn
from fastapi import FastAPI



from spotify import OAuthHandler
from youtube import YouTubeDownloader
from api import app

load_dotenv()

HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 8080))
PROTOCOL = os.getenv('PROTOCOL', 'http')
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
TESTING = os.getenv('TESTING', False)
devmode = os.getenv('DEV', False)
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://spotify-sync.ditto.rlab.uk/callback')

def check_env():
    assert client_id, "SPOTIPY_CLIENT_ID is not set"
    assert client_secret, "SPOTIPY_CLIENT_SECRET is not set"
    assert REDIRECT_URI, "REDIRECT_URI is not set"

def auth(server_class=http.server.HTTPServer, handler_class=OAuthHandler):
    server_address = (HOST, PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Please visit {PROTOCOL}://{HOST}:{PORT} to authenticate with Spotify")
    for i in range(2):
        httpd.handle_request()


def run_api_server():
    if devmode:
        print(f"Running in dev mode on port {PORT}")
        uvicorn.run(app, host=HOST, port=PORT, reload=True)
    else:
        print(f"Running API server on port {PORT}")
        uvicorn.run(app, host=HOST, port=PORT)



def run(parser):
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    try:
        if sp.current_user() is None:
            raise spotipy.SpotifyException(401, -1, "Invalid access token")
    except spotipy.SpotifyException:
        parser.error("Please authenticate with Spotify first using the -a flag")
        sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

    assert sp.current_user(), "Authentication failed"

    my_playlists = sp.current_user_playlists()
    
    json_response = json.dumps(my_playlists)
    os.makedirs('data', exist_ok=True)
    
    for playlist in my_playlists['items']:
        playlist_name = playlist['name']
        playlist_dir = f"data/{playlist_name}"

        # Skip processing if playlist directory already exists
        if os.path.exists(playlist_dir):
            print(f"Skipping playlist {playlist_name}, already processed.")
            continue
        
        os.makedirs(playlist_dir, exist_ok=True)
        print(f"Processing playlist {playlist_name}...")
        
        # Fetch tracks and save to file
        tracks = sp.playlist_tracks(playlist['id'])
        with open(f"{playlist_dir}/tracks.json", 'w') as playlist_file:
            playlist_file.write(json.dumps(tracks))
        
        for track in tracks['items']:
            track_itm = track.get('track', {}) if track else None
            track_name = track_itm.get('name', {}) if track_itm else None
            track_dir = f"{playlist_dir}/{track_name}"
            
            # Skip processing if track directory already exists
            if os.path.exists(track_dir):
                print(f"Skipping track {track_name}, already processed.")
                continue

            if not track_name:
                print(f"Skipping track {track_name}, no name found.")
                continue
            
            os.makedirs(track_dir, exist_ok=True)

            # Save track info
            track_info_file = f"{track_dir}/info.json"
            if not os.path.exists(track_info_file):
                song_info = sp.track(track['track']['id'])
                with open(track_info_file, 'w') as f:
                    f.write(json.dumps(song_info))
            
            # Save track features
            track_features_file = f"{track_dir}/features.json"
            if not os.path.exists(track_features_file):
                features = sp.audio_features(track['track']['id'])
                with open(track_features_file, 'w') as f:
                    f.write(json.dumps(features))
            
            # Save track image
            track_image_file = f"{track_dir}/image.jpg"
            if not os.path.exists(track_image_file):
                image_url = track['track']['album']['images'][0]['url']
                with open(track_image_file, 'wb') as image_f:
                    image_f.write(urllib.request.urlopen(image_url).read())
        
    # Process liked songs
    liked_songs_dir = 'data/liked_songs'
    os.makedirs(liked_songs_dir, exist_ok=True)
    
    liked_songs = sp.current_user_saved_tracks()
    
    for song in liked_songs['items']:
        track_name = song['track']['name']
        track_dir = f"{liked_songs_dir}/{track_name}"
        
        # Skip processing if track directory already exists
        if os.path.exists(track_dir):
            print(f"Skipping liked song {track_name}, already processed.")
            continue
        
        os.makedirs(track_dir, exist_ok=True)
        
        # Save track info
        track_info_file = f"{track_dir}/info.json"
        if not os.path.exists(track_info_file):
            song_info = sp.track(song['track']['id'])
            with open(track_info_file, 'w') as f:
                f.write(json.dumps(song_info))
        
        # Save track features
        track_features_file = f"{track_dir}/features.json"
        if not os.path.exists(track_features_file):
            features = sp.audio_features(song['track']['id'])
            with open(track_features_file, 'w') as f:
                f.write(json.dumps(features))
        
        # Save track image
        track_image_file = f"{track_dir}/image.jpg"
        if not os.path.exists(track_image_file):
            image_url = song['track']['album']['images'][0]['url']
            with open(track_image_file, 'wb') as image_f:
                image_f.write(urllib.request.urlopen(image_url).read())
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Spotify data collector')
    
    main_parser = parser.add_subparsers(dest='command')
    main_parser.required = True

    spotify_parser = main_parser.add_parser('sync', help='Sync Spotify data')
    spotify_parser.add_argument('-a', '--auth', action='store_true', help='Authenticate with Spotify')

    download_parser = main_parser.add_parser('download', help='Download Tracks from youtube')
    download_parser.add_argument('-d', '--data', help='Path to data directory', default=os.path.join(os.getcwd(), 'data'))

    api_parser = main_parser.add_parser('api', help='Run as API server')
    api_parser.add_argument('-p', '--port', help='Port to run server on', default=PORT)

    args = parser.parse_args()

    if args.command == 'api':
        run_api_server()
    
    if args.command == 'sync':
        if args.auth:
            auth()
        run(parser)

    elif args.command == 'download':
        YouTubeDownloader(args.data)
