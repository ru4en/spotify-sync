import http.server
import spotipy
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from fastapi import HTTPException
import os
from dotenv import load_dotenv
import urllib.parse
import logging

logger = logging.getLogger(__name__)


load_dotenv()
client_id = os.getenv('SPOTIPY_CLIENT_ID')
client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
HOST = os.getenv('HOST', 'localhost')
PORT = os.getenv('PORT', 8080)
PROTOCOL = os.getenv('PROTOCOL', 'http')

assert client_id is not None, "Please set SPOTIPY_CLIENT_ID environment variable"
assert client_secret is not None, "Please set SPOTIPY_CLIENT_SECRET environment variable"

REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://spotify-sync.ditto.rlab.uk/callback')

sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret,
                        redirect_uri=REDIRECT_URI, scope="playlist-read-private user-library-read")
class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            query = urllib.parse.urlparse(self.path).query
            code = urllib.parse.parse_qs(query).get('code')
            if code:
                # when successful, say successful and close the window and turn off the server
                token_info = sp_oauth.get_access_token(code[0])
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Authorization successful</h1><script>window.close()</script></body></html>')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authorization failed.')
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            auth_url = sp_oauth.get_authorize_url()
            # automatically redirect to the Spotify authentication page
            self.wfile.write(f'<html><body><script>window.location="{auth_url}"</script></body></html>'.encode('utf-8'))
            
        
def get_spotify_client():
    """Return an authenticated Spotify client or prompt for OAuth."""
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        logger.info(f"Redirecting to Spotify OAuth: {auth_url}")
        raise HTTPException(status_code=401, detail={"error": "Please authenticate with Spotify", "auth_url": auth_url})
    
    sp = Spotify(auth=token_info["access_token"])
    return sp
