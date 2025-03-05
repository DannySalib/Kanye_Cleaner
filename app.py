import os
import re
import requests # type: ignore
from flask import Flask, redirect, request, url_for, render_template # type: ignore
from urllib.parse import urlencode 

# Spotify API credentials
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Client ID or Client Secret not found in environment variables.")

REDIRECT_URI = "https://kanye-cleaner.onrender.com/callback"

# Spotify API endpoints
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1"

# Initialize Flask app
app = Flask(__name__)

# Step 1: Redirect user to Spotify authorization page
@app.route("/")
def index():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-public playlist-modify-private",  # Required permissions
        "show_dialog": True  # Optional: Force user to log in again
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}" # type: ignore
    return render_template("index.html", auth_url=auth_url)

# Step 2: Handle Spotify callback and exchange authorization code for access token
@app.route("/callback")
def callback():
    if "error" in request.args:
        return render_template("callback.html", error=request.args["error"])

    if "code" in request.args:
        code = request.args["code"]
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        response = requests.post(TOKEN_URL, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            refresh_token = token_data["refresh_token"]
            return redirect(url_for("select_playlist", access_token=access_token))
        else:
            return render_template("callback.html", error=f"Failed to retrieve access token: {response.text}")

# Step 3: Let the user input the playlist URL/URI
@app.route("/select_playlist")
def select_playlist():
    access_token = request.args.get("access_token")
    if not access_token:
        return render_template("callback.html", error="Access token missing.")

    return render_template("select_playlist.html", access_token=access_token)

# Step 4: Extract playlist ID and remove artist's tracks
@app.route("/remove_tracks", methods=["POST"])
def remove_artist_tracks():
    access_token = request.form.get("access_token")
    playlist_input = request.form.get("playlist_input")
    if not access_token or not playlist_input:
        return render_template("callback.html", error="Access token or playlist input missing.")

    # Extract playlist ID from the input
    playlist_id = extract_playlist_id(playlist_input)
    if not playlist_id:
        return render_template("callback.html", error="Invalid playlist URL or URI.")

    # Artist ID for Kanye West (replace with the desired artist ID)
    kanye_id = "5K4W6rqBFWDnAN6FQUkS6x"

    # Get playlist tracks
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(
        f"{API_BASE_URL}/playlists/{playlist_id}/tracks",
        headers=headers
    )
    if response.status_code != 200:
        return render_template("callback.html", error=f"Failed to retrieve playlist tracks: {response.text}")

    tracks = response.json()["items"]

    # Filter tracks by artist
    tracks_to_remove = []
    for track in tracks:
        for artist in track["track"]["artists"]:
            if artist["id"] == kanye_id:
                tracks_to_remove.append({"uri": track["track"]["uri"]})

    # Remove tracks from playlist
    if tracks_to_remove:
        remove_response = requests.delete(
            f"{API_BASE_URL}/playlists/{playlist_id}/tracks",
            headers=headers,
            json={"tracks": tracks_to_remove}
        )
        if remove_response.status_code == 200:
            return render_template("remove_tracks.html", message="Tracks removed successfully!")
        else:
            return render_template("callback.html", error=f"Failed to remove tracks: {remove_response.text}")
    else:
        return render_template("remove_tracks.html", message="No tracks to remove.")

def extract_playlist_id(playlist_input):
    """
    Extracts the playlist ID from a Spotify playlist URL or URI.
    """
    # Regex to match Spotify playlist URLs and URIs
    url_pattern = r"https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
    uri_pattern = r"spotify:playlist:([a-zA-Z0-9]+)"

    # Check if the input is a URL
    url_match = re.search(url_pattern, playlist_input)
    if url_match:
        return url_match.group(1)

    # Check if the input is a URI
    uri_match = re.search(uri_pattern, playlist_input)
    if uri_match:
        return uri_match.group(1)

    # If no match, assume the input is already a playlist ID
    return playlist_input

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

