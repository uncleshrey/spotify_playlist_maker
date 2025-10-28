import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import os
import time
import random
import re
from spotipy.exceptions import SpotifyException
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

# Spotify API credentials - read from environment (recommended) with fallbacks
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID', 'b3dbd3bbe68d4f38bf3a735a0ec18b80')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET', '4b59e772264149abbc31f3e8c3dd48e1')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI', 'http://127.0.0.1:8000')

def read_songs_from_file(filename):
    """Read songs from a text file. Accepts hyphen, en-dash, em-dash as separator."""
    songs = []

    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found!")
        return None

    sep_chars = ['–', '-', '—']  # en-dash, hyphen, em-dash
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue

                # normalize non-breaking spaces
                raw = raw.replace('\u00A0', ' ')

                # find first separator occurrence
                sep_used = None
                for s in sep_chars:
                    if s in raw:
                        sep_used = s
                        break

                if not sep_used:
                    # skip lines without a recognized separator
                    continue

                left, right = raw.split(sep_used, 1)
                song_name = left.strip().strip('"').strip("'")
                context = right.strip()

                if song_name and context:
                    songs.append((song_name, context))

        print(f"✓ Loaded {len(songs)} songs from {filename}\n")
        return songs

    except Exception as e:
        print(f"Error reading file: {e}")
        return None


def safe_search(sp, query, type='track', limit=5, retries=3):
    """Search wrapper with retry/backoff and basic 429 handling."""
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            return sp.search(q=query, type=type, limit=limit)
        except SpotifyException as e:
            status = getattr(e, 'http_status', None)
            headers = getattr(e, 'headers', {}) or {}
            if status == 429:
                retry_after = int(headers.get('Retry-After', 1))
                print(f"Rate limited. Sleeping for {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            else:
                if attempt < retries:
                    sleep_time = backoff + random.random()
                    print(f"Search error (attempt {attempt}/{retries}): {e}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    backoff *= 2
                    continue
                else:
                    raise
        except Exception as e:
            if attempt < retries:
                sleep_time = backoff + random.random()
                print(f"Search error (attempt {attempt}/{retries}): {e}. Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                backoff *= 2
                continue
            else:
                raise
    return None


def search_and_add_songs(sp, playlist_id, songs):
    """Search for songs and add them to the playlist"""
    track_uris = []
    not_found = []

    for song_name, context in songs:
        # Use a slightly stricter query to prefer exact track matches
        query = f'track:"{song_name}" {context}'
        print(f"Searching for: {song_name} - {context}")

        try:
            results = safe_search(sp, query, type='track', limit=5)

            if results and results.get('tracks', {}).get('items'):
                # Get the first result
                track = results['tracks']['items'][0]
                track_uris.append(track['uri'])
                print(f"✓ Found: {track['name']} by {track['artists'][0]['name']}")
            else:
                not_found.append(f"{song_name} - {context}")
                print(f"✗ Not found: {song_name}")
        except Exception as e:
            print(f"Error searching for {song_name}: {e}")
            not_found.append(f"{song_name} - {context}")

    # Deduplicate URIs while preserving order
    seen = set()
    unique_uris = []
    for uri in track_uris:
        if uri not in seen:
            seen.add(uri)
            unique_uris.append(uri)
    track_uris = unique_uris

    # Add tracks to playlist in batches of 100 (Spotify's limit)
    if track_uris:
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            try:
                sp.playlist_add_items(playlist_id, batch)
            except Exception as e:
                print(f"Error adding batch to playlist: {e}")
        print(f"\n✓ Successfully added {len(track_uris)} songs to the playlist!")

    if not_found:
        print(f"\n✗ Could not find {len(not_found)} songs:")
        for song in not_found:
            print(f"  - {song}")

    return len(track_uris), len(not_found)

def launch_gui():
    root = tk.Tk()
    root.title("Spotify Playlist Creator")
    root.geometry("760x520")

    # Top frame for inputs
    frame = tk.Frame(root)
    frame.pack(fill='x', padx=10, pady=8)

    tk.Label(frame, text="Song file:").grid(row=0, column=0, sticky='w')
    file_var = tk.StringVar()
    file_entry = tk.Entry(frame, textvariable=file_var, width=70)
    file_entry.grid(row=0, column=1, sticky='w')

    def browse_file():
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            file_var.set(path)
            # set default playlist name if empty
            if not playlist_name_var.get():
                playlist_name_var.set(os.path.splitext(os.path.basename(path))[0].replace('_', ' '))

    tk.Button(frame, text="Browse", command=browse_file).grid(row=0, column=2, padx=6)

    tk.Label(frame, text="Playlist name:").grid(row=1, column=0, sticky='w')
    playlist_name_var = tk.StringVar()
    playlist_entry = tk.Entry(frame, textvariable=playlist_name_var, width=70)
    playlist_entry.grid(row=1, column=1, sticky='w')

    public_var = tk.BooleanVar(value=True)
    tk.Checkbutton(frame, text="Public", variable=public_var).grid(row=2, column=1, sticky='w')

    # Ensure use_filename_var and its handler exist (guard in case of previous edits changing order)
    try:
        use_filename_var
    except NameError:
        use_filename_var = tk.BooleanVar(value=True)
        def on_use_filename_changed(*_):
            use_fn = use_filename_var.get()
            if use_fn:
                p = file_var.get().strip()
                if p:
                    playlist_name_var.set(os.path.splitext(os.path.basename(p))[0].replace('_', ' '))
                playlist_entry.configure(state='disabled')
            else:
                playlist_entry.configure(state='normal')

    # Manual entry option: allow user to type/paste song lines instead of using a file
    manual_var = tk.BooleanVar(value=False)
    def on_manual_changed(*_):
        is_manual = manual_var.get()
        # Enable/disable file controls
        for child in frame.winfo_children():
            try:
                if isinstance(child, tk.Entry) and child is file_entry:
                    child.configure(state='disabled' if is_manual else 'normal')
                if isinstance(child, tk.Button) and child.cget('text') == 'Browse':
                    child.configure(state='disabled' if is_manual else 'normal')
            except Exception:
                pass
        # Show/hide manual text widget
        if is_manual:
            manual_label.grid(row=3, column=0, sticky='nw', pady=(6,0))
            manual_text.grid(row=3, column=1, columnspan=2, sticky='we', pady=(6,0))
            playlist_entry.configure(state='normal')
            use_filename_var.set(False)
            on_use_filename_changed()
        else:
            manual_label.grid_remove()
            manual_text.grid_remove()
            on_use_filename_changed()

    tk.Checkbutton(frame, text='Manual entries (paste lines)', variable=manual_var, command=on_manual_changed).grid(row=2, column=3, sticky='e')

    manual_label = tk.Label(frame, text='Manual songs (one per line, format: Song – Artist)')
    manual_text = scrolledtext.ScrolledText(frame, height=6)
    manual_label.grid_remove()
    manual_text.grid_remove()

    def parse_manual_text(text:str):
        """Parse manual multiline input into list of (song_name, context)."""
        lines = [ln.strip() for ln in text.splitlines()]
        sep_chars = ['–', '-', '—']
        parsed = []
        for raw in lines:
            if not raw:
                continue
            raw = raw.replace('\u00A0', ' ')
            sep_used = None
            for s in sep_chars:
                if s in raw:
                    sep_used = s
                    break
            if not sep_used:
                # if no separator, treat whole line as song name with empty context
                parsed.append((raw, ''))
                continue
            left, right = raw.split(sep_used, 1)
            song_name = left.strip().strip('"').strip("'")
            context = right.strip()
            if song_name:
                parsed.append((song_name, context))
        return parsed

    def get_songs_from_inputs(filepath):
        """Return list of (song, context) from manual text if enabled, else from file path."""
        if manual_var.get():
            text = manual_text.get('1.0', 'end')
            songs = parse_manual_text(text)
            return songs
        # else fallback to file
        return read_songs_from_file(filepath)

    # Dark theme toggle
    dark_theme_var = tk.BooleanVar(value=False)

    def apply_theme(is_dark: bool, widget_root=None):
        """Apply dark or light theme to all widgets by walking the widget tree.
        This avoids referencing outer variables that may not be bound yet.
        """
        bg = '#2e2e2e' if is_dark else 'SystemButtonFace'
        fg = '#ffffff' if is_dark else 'black'
        entry_bg = '#3a3a3a' if is_dark else 'white'
        txt_bg = '#1e1e1e' if is_dark else 'white'
        btn_bg = '#4CAF50' if is_dark else '#4CAF50'
        preview_btn_bg = '#1976D2' if is_dark else '#2196F3'

        roots = [root]
        if widget_root:
            roots.append(widget_root)

        def walk_and_style(w):
            # Try to set generic background for frames/windows
            try:
                if isinstance(w, (tk.Tk, tk.Toplevel, tk.Frame)):
                    w.configure(bg=bg)
            except Exception:
                pass

            # Style specific widget types
            try:
                if isinstance(w, tk.Label):
                    w.configure(bg=bg, fg=fg)
                elif isinstance(w, tk.Entry):
                    w.configure(bg=entry_bg, fg=fg, insertbackground=fg)
                elif isinstance(w, tk.Checkbutton):
                    w.configure(bg=bg, fg=fg, selectcolor=bg)
                elif isinstance(w, tk.Button):
                    # Try to detect preview button by its text
                    txt = ''
                    try:
                        txt = w.cget('text')
                    except Exception:
                        txt = ''
                    if 'Preview' in txt:
                        w.configure(bg=preview_btn_bg, fg='white')
                    else:
                        w.configure(bg=btn_bg, fg='white')
                elif isinstance(w, scrolledtext.ScrolledText):
                    w.configure(bg=txt_bg, fg=fg, insertbackground=fg)
            except Exception:
                pass

            # Recurse into children
            try:
                for child in w.winfo_children():
                    walk_and_style(child)
            except Exception:
                pass

        for r in roots:
            walk_and_style(r)

        # ensure the main log widget uses txt colors if present
        try:
            log.configure(bg=txt_bg, fg=fg, insertbackground=fg)
        except Exception:
            pass

    def on_dark_theme_changed():
        apply_theme(dark_theme_var.get())

    tk.Checkbutton(frame, text='Dark theme', variable=dark_theme_var, command=on_dark_theme_changed).grid(row=2, column=2, sticky='w')

    # ensure initial state
    on_use_filename_changed()
    apply_theme(dark_theme_var.get())

    # update browse_file to respect use_filename_var
    _old_browse = browse_file
    def _browse_and_update():
        _old_browse()
        if use_filename_var.get():
            p = file_var.get().strip()
            if p:
                playlist_name_var.set(os.path.splitext(os.path.basename(p))[0].replace('_', ' '))
    # replace the button command
    # find the Browse button (it's the last added in frame children) and rebind
    try:
        # brute-force: iterate frame children to find the Button with text 'Browse'
        for child in frame.winfo_children():
            if isinstance(child, tk.Button) and child.cget('text') == 'Browse':
                child.configure(command=_browse_and_update)
                break
    except Exception:
        pass

    # modify preview popup and playlist creation to apply theme to new windows
    # wrap original show_preview_window by patching the inner function where it is defined later via root.after calls
    # To keep changes localized, monkeypatch apply_theme into the global namespace for popup use
    globals()['apply_theme'] = apply_theme

    # Buttons frame
    buttons = tk.Frame(root)
    buttons.pack(fill='x', padx=10)

    start_btn = tk.Button(buttons, text="Create Playlist", bg='#4CAF50', fg='white')
    start_btn.pack(side='left')

    clear_btn = tk.Button(buttons, text="Clear Log")
    clear_btn.pack(side='left', padx=6)

    # Preview button
    preview_btn = tk.Button(buttons, text="Preview Matches", bg='#2196F3', fg='white')
    preview_btn.pack(side='left', padx=6)

    # Log area
    log = scrolledtext.ScrolledText(root, state='disabled', height=22)
    log.pack(fill='both', expand=True, padx=10, pady=10)

    def write_log(msg: str):
        log.configure(state='normal')
        log.insert('end', msg)
        if not msg.endswith('\n'):
            log.insert('end', '\n')
        log.see('end')
        log.configure(state='disabled')

    class StdoutRedirector:
        def write(self, s):
            if s and s.strip():
                root.after(0, write_log, s.rstrip())
        def flush(self):
            pass

    def clear_log():
        log.configure(state='normal')
        log.delete('1.0', 'end')
        log.configure(state='disabled')

    clear_btn.configure(command=clear_log)

    def start_process():
        filepath = file_var.get().strip()
        if not manual_var.get() and not filepath:
            messagebox.showerror("Missing file", "Please select a song file to continue.")
            return
        if not manual_var.get() and not os.path.exists(filepath):
            messagebox.showerror("File not found", "The selected file does not exist.")
            return

        playlist_name = playlist_name_var.get().strip() or os.path.splitext(os.path.basename(filepath))[0].replace('_', ' ')
        public = public_var.get()

        start_btn.configure(state='disabled')

        def worker():
            old_stdout = sys.stdout
            sys.stdout = StdoutRedirector()
            try:
                print('=' * 60)
                print('Starting playlist creation...')
                songs = get_songs_from_inputs(filepath)
                if not songs:
                    print('No songs found or error reading input!')
                    return

                scope = "playlist-modify-public playlist-modify-private"
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    redirect_uri=REDIRECT_URI,
                    scope=scope
                ))

                user = sp.current_user()
                print(f"Logged in as: {user.get('display_name')}")

                playlist = sp.user_playlist_create(
                    user=user['id'],
                    name=playlist_name,
                    public=public,
                    description=f'Created from {filepath}'
                )

                print(f"Created playlist: {playlist_name}")
                print(f"Playlist URL: {playlist['external_urls']['spotify']}")

                added, not_found = search_and_add_songs(sp, playlist['id'], songs)
                print(f"\n{'='*60}")
                print(f"Summary: {added} songs added, {not_found} not found")
                print(f"{'='*60}")
                print(f"Your playlist is ready! Open it here:")
                print(playlist['external_urls']['spotify'])

            except Exception as e:
                print(f"Error during operation: {e}")
            finally:
                sys.stdout = old_stdout
                root.after(0, lambda: start_btn.configure(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

    start_btn.configure(command=start_process)

    def create_playlist_with_uris(sp_obj, playlist_name, public_flag, source_path, uris):
        """Create a playlist and add the provided URIs. Intended to run in a background thread."""
        # Redirect stdout to GUI
        old_stdout = sys.stdout
        sys.stdout = StdoutRedirector()
        try:
            print('=' * 60)
            print('Creating playlist from preview...')
            user = sp_obj.current_user()
            print(f"Logged in as: {user.get('display_name')}")

            playlist = sp_obj.user_playlist_create(
                user=user['id'],
                name=playlist_name,
                public=public_flag,
                description=f'Created from {source_path} (preview)'
            )

            print(f"Created playlist: {playlist_name}")
            print(f"Playlist URL: {playlist['external_urls']['spotify']}")

            # Add tracks in batches
            for i in range(0, len(uris), 100):
                batch = uris[i:i+100]
                try:
                    sp_obj.playlist_add_items(playlist['id'], batch)
                except Exception as e:
                    print(f"Error adding batch to playlist: {e}")
            print(f"\n✓ Successfully added {len(uris)} songs to the playlist!")
            print(f"Your playlist is ready! Open it here:")
            print(playlist['external_urls']['spotify'])

        except Exception as e:
            print(f"Error creating playlist from preview: {e}")
        finally:
            sys.stdout = old_stdout
            root.after(0, lambda: start_btn.configure(state='normal'))

    def preview_matches():
        filepath = file_var.get().strip()
        if not manual_var.get() and not filepath:
            messagebox.showerror("Missing file", "Please select a song file to continue.")
            return
        if not manual_var.get() and not os.path.exists(filepath):
            messagebox.showerror("File not found", "The selected file does not exist.")
            return

        playlist_name = playlist_name_var.get().strip() or os.path.splitext(os.path.basename(filepath))[0].replace('_', ' ')
        public = public_var.get()

        preview_btn.configure(state='disabled')

        def worker_preview():
            # Create Spotify client for preview
            try:
                sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    redirect_uri=REDIRECT_URI,
                    scope="playlist-modify-public playlist-modify-private"
                ))
            except Exception as e:
                root.after(0, lambda: write_log(f"Error during auth for preview: {e}"))
                root.after(0, lambda: preview_btn.configure(state='normal'))
                return

            try:
                songs = get_songs_from_inputs(filepath)
                if not songs:
                    root.after(0, lambda: write_log('No songs found or error reading input!'))
                    root.after(0, lambda: preview_btn.configure(state='normal'))
                    return

                found = []
                not_found_local = []
                for song_name, context in songs:
                    query = f'track:"{song_name}" {context}'
                    root.after(0, lambda q=query: write_log(f"Searching for: {q}"))
                    try:
                        results = safe_search(sp, query, type='track', limit=5)
                        items = results.get('tracks', {}).get('items') if results else []
                        if items:
                            track = items[0]
                            found.append((song_name, track['name'], track['artists'][0]['name'], track['uri']))
                            root.after(0, lambda t=track: write_log(f"✓ Found: {t['name']} by {t['artists'][0]['name']} (URI: {t['uri']})"))
                        else:
                            not_found_local.append(f"{song_name} - {context}")
                            root.after(0, lambda s=song_name: write_log(f"✗ Not found: {s}"))
                    except Exception as e:
                        not_found_local.append(f"{song_name} - {context}")
                        root.after(0, lambda e=e, s=song_name: write_log(f"Error searching for {s}: {e}"))

                # Show preview window with results
                def show_preview_window():
                    pv = tk.Toplevel(root)
                    pv.title('Preview Matches')
                    pv.geometry('640x420')

                    info = tk.Label(pv, text=f"Preview for playlist: {playlist_name} — {len(found)} matches, {len(not_found_local)} not found")
                    info.pack(anchor='w', padx=8, pady=6)

                    txt = scrolledtext.ScrolledText(pv, height=18)
                    txt.pack(fill='both', expand=True, padx=8, pady=6)
                    for sname, tname, artist, uri in found:
                        txt.insert('end', f"{sname} -> {tname} — {artist} (URI: {uri})\n")
                    if not_found_local:
                        txt.insert('end', '\nNot found:\n')
                        for nf in not_found_local:
                            txt.insert('end', f"  - {nf}\n")
                    txt.configure(state='disabled')

                    btn_frame = tk.Frame(pv)
                    btn_frame.pack(fill='x', padx=8, pady=8)

                    def create_from_preview():
                        if not found:
                            messagebox.showinfo('No matches', 'No matched tracks to create a playlist from.')
                            return
                        uris = [u for (_s, _t, _a, u) in found]
                        pv.destroy()
                        # run creation in background
                        threading.Thread(target=create_playlist_with_uris, args=(sp, playlist_name, public, filepath, uris), daemon=True).start()

                    create_btn = tk.Button(btn_frame, text='Create Playlist from Matches', bg='#4CAF50', fg='white', command=create_from_preview)
                    create_btn.pack(side='left')

                    close_btn = tk.Button(btn_frame, text='Close', command=pv.destroy)
                    close_btn.pack(side='right')

                root.after(0, show_preview_window)

            finally:
                root.after(0, lambda: preview_btn.configure(state='normal'))

        threading.Thread(target=worker_preview, daemon=True).start()

    preview_btn.configure(command=preview_matches)

    root.mainloop()


# Replace CLI entrypoint with GUI launcher
def main():
    print("=" * 60)
    print("Spotify Playlist Creator")
    print("=" * 60)
    
    # Check if filename is provided
    if len(sys.argv) < 2:
        print("\nUsage: python script.py <song_file.txt> [playlist_name]")
        print("\nExample:")
        print("  python script.py Bollywood_Party_Playlist.txt")
        print("  python script.py songs.txt \"My Awesome Playlist\"")
        print("\nFile format: Each line should be:")
        print("  Song Name – Movie/Artist Name")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    # Get playlist name (use filename without extension as default)
    if len(sys.argv) >= 3:
        playlist_name = sys.argv[2]
    else:
        playlist_name = os.path.splitext(os.path.basename(filename))[0].replace('_', ' ')
    
    playlist_description = f'Created from {filename}'
    
    print(f"\nReading songs from: {filename}")
    print(f"Playlist name: {playlist_name}\n")
    
    # Read songs from file
    songs = read_songs_from_file(filename)
    if not songs:
        print("No songs found or error reading file!")
        sys.exit(1)
    
    # Set up authentication
    scope = "playlist-modify-public playlist-modify-private"
    
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=scope
    ))
    
    # Get current user
    user = sp.current_user()
    print(f"Logged in as: {user['display_name']}\n")
    
    # Create the playlist
    playlist = sp.user_playlist_create(
        user=user['id'],
        name=playlist_name,
        public=True,
        description=playlist_description
    )
    
    print(f"Created playlist: {playlist_name}")
    print(f"Playlist URL: {playlist['external_urls']['spotify']}\n")
    
    # Search and add songs
    added, not_found = search_and_add_songs(sp, playlist['id'], songs)
    
    print(f"\n{'='*60}")
    print(f"Summary: {added} songs added, {not_found} not found")
    print(f"{'='*60}")
    print(f"\nYour playlist is ready! Open it here:")
    print(playlist['external_urls']['spotify'])

if __name__ == "__main__":
    # Launch GUI instead of CLI
    launch_gui()