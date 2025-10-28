Spotify Playlist Creator — User Manual
=====================================

Overview
--------
Small Tkinter GUI that creates Spotify playlists from either a text file or manual song entries. Features:
- File picker or manual paste area for song lines
- Preview matched tracks before creating playlist
- Create playlist (public or private)
- Use filename as playlist name option
- Dark theme toggle
- Scrollable log with progress and results
- Retry/backoff handling for Spotify API rate-limits

Requirements
------------
- Python 3.8+
- spotipy package
- Spotify Developer app (Client ID, Client Secret) and Redirect URI configured (e.g. http://127.0.0.1:8000)

Quick install (PowerShell)
--------------------------
1. Install dependency:
   python -m pip install spotipy

2. Set Spotify credentials for the session (replace values):
   $env:SPOTIPY_CLIENT_ID="your_client_id"; $env:SPOTIPY_CLIENT_SECRET="your_client_secret"; $env:SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000"

3. Run the GUI:
   python "auto.py"

GUI Walkthrough
----------------
Top Inputs
- Song file: choose a UTF-8 text file with one song per line (use Browse).
- Playlist name: editable. If "Use filename as playlist name" is checked this is auto-filled and disabled.
- Public: checkbox for playlist visibility.

Options
- Use filename as playlist name: checked by default.
- Dark theme: toggles UI colors.
- Manual entries (paste lines): toggles a multiline text area where you can paste song lines one per line.

Manual entry format
- Supported separators: hyphen (-), en-dash (–), em-dash (—).
- Examples:
  - Tum Hi Ho – Arijit Singh
  - Shape of You - Ed Sheeran
  - Kala Chashma — Neha Kakkar
- Lines without a separator are treated as song name only (no context).

Preview Matches
- Click Preview Matches to run searches without creating a playlist.
- A popup lists matched track name, artist and URI and not-found items.
- From the preview you can create a playlist containing only matched tracks.

Create Playlist
- Click Create Playlist to create the playlist and add matched tracks.
- The app deduplicates URIs and adds tracks in batches (Spotify limit: 100 per request).

OAuth
- The app opens a browser for Spotify OAuth on first use. Sign in and approve the scopes.
- Make sure the Redirect URI set in your Spotify app equals SPOTIPY_REDIRECT_URI.

Troubleshooting
---------------
- "No songs found": check separators and UTF-8 encoding.
- OAuth redirect errors: ensure Redirect URI match in Spotify Dashboard.
- Rate limits (429): the app waits and retries according to Retry-After header.
- If spotipy install fails: run PowerShell as Administrator or use a virtualenv.

Example test file
-----------------
Create a file test_songs.txt with:
Tum Hi Ho – Arijit Singh
Shape of You - Ed Sheeran
