import os
import re
import glob
import shutil
import time
from pathlib import Path
import yt_dlp
from yt_dlp.utils import DownloadCancelled

# Regex to strip all ANSI terminal color escape codes
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def clean_ansi(text):
    """Remove ANSI escape sequences from strings."""
    if not text:
        return ""
    return ANSI_ESCAPE.sub("", str(text)).strip()

def setup_environment():
    """Locate FFmpeg, Deno, and aria2c (checks local app folder, bin/ folder, and system paths)."""
    import sys
    found_bins = {}

    # Check local portable directories first (next to script or packaged .exe)
    base_dirs = []
    if getattr(sys, "frozen", False):
        base_dirs.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):
            base_dirs.append(sys._MEIPASS)
    if "__file__" in globals():
        base_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    base_dirs.append(os.getcwd())

    for base_dir in base_dirs:
        for sub in ("", "bin"):
            check_path = os.path.join(base_dir, sub)
            if os.path.isdir(check_path):
                for f in os.listdir(check_path):
                    f_lower = f.lower()
                    if f_lower in ("ffmpeg.exe", "deno.exe", "aria2c.exe") and f_lower not in found_bins:
                        full_p = os.path.join(check_path, f)
                        found_bins[f_lower] = full_p
                        if check_path not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = check_path + os.pathsep + os.environ.get("PATH", "")

    # Check local WinGet Packages
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_dir = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")
        if os.path.isdir(winget_dir):
            for root, dirs, files in os.walk(winget_dir):
                for f in files:
                    f_lower = f.lower()
                    if f_lower in ("ffmpeg.exe", "deno.exe", "aria2c.exe") and f_lower not in found_bins:
                        found_bins[f_lower] = os.path.join(root, f)
                        if root not in os.environ.get("PATH", ""):
                            os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")

    # Check PATH if still missing
    for binary_name in ("ffmpeg.exe", "deno.exe", "aria2c.exe"):
        if binary_name not in found_bins and shutil.which(binary_name):
            found_bins[binary_name] = shutil.which(binary_name)

    return found_bins

setup_environment()

def format_seconds(seconds):
    """Format duration in seconds into HH:MM:SS or MM:SS."""
    if not seconds:
        return "--:--"
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    except Exception:
        return "--:--"

def format_number(num):
    """Format numbers into human-readable notation (e.g. 1.2M, 45.6K)."""
    if not num:
        return "0"
    try:
        num = int(num)
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        if num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)
    except Exception:
        return str(num)

def fetch_media_info(url):
    """
    Extract metadata for a YouTube URL (detects whether it's a playlist or a single video).
    """
    setup_environment()
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "no_color": True,
        "socket_timeout": 30,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        info_type = info.get("_type", "")
        entries = list(info.get("entries", [])) if "entries" in info else []
        is_playlist = (info_type == "playlist") or (len(entries) > 1)

        if is_playlist:
            first_entry = entries[0] if entries else {}
            return {
                "is_playlist": True,
                "title": clean_ansi(info.get("title", "YouTube Playlist")),
                "uploader": clean_ansi(info.get("uploader") or info.get("channel", "Unknown Channel")),
                "item_count": len(entries) if entries else info.get("playlist_count", 0),
                "duration": f"{len(entries)} items" if entries else "Playlist",
                "views": "Playlist",
                "thumbnail": info.get("thumbnail") or first_entry.get("thumbnail") or (first_entry.get("thumbnails", [{}])[0].get("url") if first_entry.get("thumbnails") else None),
                "id": info.get("id"),
                "webpage_url": info.get("webpage_url", url),
            }
        else:
            return {
                "is_playlist": False,
                "title": clean_ansi(info.get("title", "Unknown Title")),
                "uploader": clean_ansi(info.get("uploader") or info.get("channel", "Unknown Channel")),
                "duration": format_seconds(info.get("duration")),
                "views": format_number(info.get("view_count")),
                "thumbnail": info.get("thumbnail"),
                "id": info.get("id"),
                "webpage_url": info.get("webpage_url", url),
            }

def find_neat_download_manager():
    """Detect Neat Download Manager executable location on the host machine."""
    potential_paths = [
        r"C:\Program Files (x86)\Neat Download Manager\NeatDM.exe",
        r"C:\Program Files\Neat Download Manager\NeatDM.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Neat Download Manager\NeatDM.exe"),
    ]
    for p in potential_paths:
        if os.path.isfile(p):
            return p
    return shutil.which("NeatDM.exe") or shutil.which("NeatDM")

def extract_direct_stream_urls(url, quality="Best Quality (Auto)"):
    """
    Extract deciphered, unthrottled direct media stream URLs for export to external download managers (e.g., NeatDM).
    """
    setup_environment()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "skip_download": True,
        "socket_timeout": 30,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])

        # Filter audio streams
        audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
        best_audio = audio_formats[-1] if audio_formats else None

        is_audio = "Audio Only" in quality
        if is_audio and best_audio:
            ext_label = best_audio.get("ext") or "audio"
            return {
                "title": clean_ansi(info.get("title", "Audio Stream")),
                "direct_url": best_audio.get("url"),
                "audio_url": best_audio.get("url"),
                "is_audio_only": True,
                "is_muxed": False,
                "resolution": f"Audio ({ext_label})",
            }

        max_h = 99999
        if "1080p" in quality:
            max_h = 1080
        elif "720p" in quality:
            max_h = 720
        elif "480p" in quality:
            max_h = 480
        elif "360p" in quality:
            max_h = 360

        matching_videos = [f for f in formats if f.get("vcodec") != "none" and (f.get("height") or 0) <= max_h]
        best_vid = matching_videos[-1] if matching_videos else (formats[-1] if formats else None)

        is_muxed = bool(best_vid and best_vid.get("acodec") != "none")
        res_label = best_vid.get("resolution") if best_vid else "Best"
        if not res_label and best_vid and best_vid.get("height"):
            res_label = f"{best_vid.get('height')}p"

        return {
            "title": clean_ansi(info.get("title", "Video Stream")),
            "direct_url": best_vid.get("url") if best_vid else None,
            "audio_url": best_audio.get("url") if best_audio else None,
            "is_audio_only": False,
            "is_muxed": is_muxed,
            "resolution": res_label or "Best",
        }

def cleanup_partial_files(target_dir):
    """Safely remove leftover .part and .ytdl files from a directory."""
    if not os.path.exists(target_dir):
        return
    try:
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.endswith(".part") or file.endswith(".ytdl"):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
    except Exception:
        pass

def download_media(
    url,
    output_folder,
    quality="Best Quality (Auto)",
    download_playlist=False,
    progress_callback=None,
    cancel_check=None
):
    """
    High-speed, resilient download with instant cancellation and .part cleanup.
    """
    setup_environment()

    if download_playlist:
        outtmpl = os.path.join(
            output_folder,
            "%(playlist_title,playlist)s",
            "%(playlist_index)02d - %(title)s.%(ext)s"
        )
    else:
        outtmpl = os.path.join(output_folder, "%(title)s.%(ext)s")

    last_report_time = 0
    tracked_files = set()

    def hook(d):
        nonlocal last_report_time

        # Track the filename currently being downloaded
        current_fn = d.get("filename")
        if current_fn:
            tracked_files.add(current_fn)
            tracked_files.add(current_fn + ".part")

        # INSTANT CANCELLATION:
        # We must raise yt_dlp's native DownloadCancelled, because yt-dlp specifically
        # re-raises this and does not swallow it in ignoreerrors playlist loops!
        if cancel_check and cancel_check():
            raise DownloadCancelled("Download cancelled by user.")

        if not progress_callback:
            return

        status = d.get("status")
        now = time.time()

        if status == "downloading":
            if now - last_report_time < 0.08:
                return
            last_report_time = now

            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            percent = (downloaded / total) if total > 0 else 0.0
            percent = max(0.0, min(1.0, percent))

            info_dict = d.get("info_dict", {})
            playlist_index = info_dict.get("playlist_index")
            n_entries = info_dict.get("n_entries") or info_dict.get("playlist_count")
            current_title = clean_ansi(info_dict.get("title", ""))

            speed_str = clean_ansi(d.get("_speed_str", "N/A"))
            eta_str = clean_ansi(d.get("_eta_str", "N/A"))
            pct_str = f"{percent * 100:.1f}%"

            progress_callback({
                "status": "downloading",
                "percent": percent,
                "percent_str": pct_str,
                "speed": speed_str,
                "eta": eta_str,
                "downloaded": downloaded,
                "total": total,
                "is_playlist": bool(playlist_index),
                "playlist_index": playlist_index,
                "playlist_total": n_entries,
                "item_title": current_title,
            })
        elif status == "finished":
            info_dict = d.get("info_dict", {})
            playlist_index = info_dict.get("playlist_index")
            n_entries = info_dict.get("n_entries")

            progress_callback({
                "status": "processing",
                "percent": 1.0,
                "percent_str": "100%",
                "is_playlist": bool(playlist_index),
                "playlist_index": playlist_index,
                "playlist_total": n_entries,
                "message": "Merging and converting...",
            })

    def match_filter(info_dict, incomplete):
        # If user hit cancel before the next video starts extraction, abort immediately!
        if cancel_check and cancel_check():
            raise DownloadCancelled("Download cancelled by user.")
        return None

    found_bins = setup_environment()
    aria2_bin = found_bins.get("aria2c.exe")

    ydl_opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [hook],
        "match_filter": match_filter,
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "windowsfilenames": True,
        "socket_timeout": 45,
        "retries": 20,
        "fragment_retries": 20,
        "file_access_retries": 10,
        "extractor_retries": 5,
        "concurrent_fragment_downloads": 16,
        "buffersize": 4 * 1024 * 1024,
        "http_chunk_size": 10485760,
        "noplaylist": not download_playlist,
        "ignoreerrors": True if download_playlist else False,
    }

    if quality == "Audio Only (MP3)":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif quality == "Audio Only (M4A)":
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio"
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "m4a",
        }]
    elif quality == "1080p (Full HD)":
        ydl_opts["format"] = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        ydl_opts["merge_output_format"] = "mp4"
    elif quality == "720p (HD)":
        ydl_opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        ydl_opts["merge_output_format"] = "mp4"
    elif quality == "480p (SD)":
        ydl_opts["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
        ydl_opts["merge_output_format"] = "mp4"
    elif quality == "360p (Low)":
        ydl_opts["format"] = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
        ydl_opts["merge_output_format"] = "mp4"
    else:
        ydl_opts["format"] = "bestvideo+bestaudio/best"
        ydl_opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadCancelled:
        # Clean up any partial files that were written
        for f in tracked_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        cleanup_partial_files(output_folder)
        raise
