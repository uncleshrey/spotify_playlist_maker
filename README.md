Spotify Playlist Creator
=======================

A small Python Tkinter GUI that builds Spotify playlists from a text file or pasted/manual song entries. It uses spotipy for Spotify Web API access and supports previewing matches before creating a playlist.

Features
--------
- Load songs from a UTF-8 text file or paste manual song lines
- Preview matched tracks (name, artist, URI) before creating the playlist
- Create public or private playlists
- Use filename as playlist name (optional)
- Dark theme toggle and scrollable operation log
- Retry/backoff handling for API rate limits and batched adds (100 tracks per request)

Requirements
------------
- Python 3.8+
- spotipy
- A Spotify Developer App (Client ID, Client Secret) and a Redirect URI configured (e.g. http://127.0.0.1:8000)

Installation (PowerShell)
-------------------------
1. Install dependencies:
   python -m pip install spotipy

2. Set Spotify credentials for the session (replace values):
   $env:SPOTIPY_CLIENT_ID="your_client_id"; $env:SPOTIPY_CLIENT_SECRET="your_client_secret"; $env:SPOTIPY_REDIRECT_URI="http://127.0.0.1:8000"

Running
-------
- Launch the GUI:
  python auto.py

- CLI mode (older behavior still present in the script):
  python auto.py <song_file.txt> [playlist_name]

File format
-----------
Each line should represent one song. Supported separators between song and context are hyphen (-), en-dash (–) and em-dash (—). Lines without a separator are treated as song name only.

Example file (test_songs.txt)
-----------------------------
Tum Hi Ho – Arijit Singh
Shape of You - Ed Sheeran

Usage notes
-----------
- Preview matches before creating playlists to avoid unexpected results.
- For large lists, the app deduplicates URIs and uploads tracks in batches of up to 100.
- Do not commit client secrets. Use environment variables or a secure vault.

Troubleshooting
---------------
- OAuth redirect errors: ensure the Redirect URI in your Spotify app settings matches SPOTIPY_REDIRECT_URI.
- If spotipy installation fails, run PowerShell as Administrator or use a virtual environment.

Contributing
------------
Pull requests and issues are welcome. Useful enhancements: per-line selection in preview, saving/loading manual drafts, or fuzzy search fallbacks.

License
-------
This project has no license file in the repository. Add a LICENSE if you want to specify terms.

Contact
-------
If you want me to push this file to your remote, run the git commands locally and paste any errors here.
