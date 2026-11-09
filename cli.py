import os
import sys
import argparse
from pathlib import Path

import downloader

def print_progress(data):
    status = data.get("status")
    if status == "downloading":
        pct = data.get("percent_str", "0%")
        speed = data.get("speed", "N/A")
        eta = data.get("eta", "N/A")
        
        is_playlist = data.get("is_playlist")
        p_idx = data.get("playlist_index")
        p_total = data.get("playlist_total")

        if is_playlist and p_idx and p_total:
            sys.stdout.write(f"\r[Video {p_idx}/{p_total}] Progress: {pct} | Speed: {speed} | ETA: {eta}   ")
        else:
            sys.stdout.write(f"\rProgress: {pct} | Speed: {speed} | ETA: {eta}   ")
        sys.stdout.flush()
    elif status == "processing":
        sys.stdout.write("\nMerging and finalizing formats...\n")
        sys.stdout.flush()

def interactive_mode():
    print("=" * 60)
    print("      YouTube Video & Playlist Downloader (CLI)       ")
    print("=" * 60)

    url = input("\nEnter YouTube URL: ").strip()
    if not url:
        print("Error: URL cannot be empty.")
        return

    print("\nFetching information...")
    is_playlist = False
    try:
        info = downloader.fetch_media_info(url)
        is_playlist = info.get("is_playlist", False)
        print(f"\nTitle:    {info['title']}")
        print(f"Channel:  {info['uploader']}")
        if is_playlist:
            print(f"Type:     📑 Playlist ({info.get('item_count', 0)} videos)")
        else:
            print(f"Duration: {info['duration']}")
            print(f"Views:    {info['views']}")
    except Exception as e:
        print(f"Warning: Could not fetch preview info ({e}). Proceeding...")

    download_full_playlist = False
    if is_playlist:
        ans = input("\nDownload entire playlist? [Y/n]: ").strip().lower()
        download_full_playlist = ans != "n"

    print("\nSelect Download Quality / Format:")
    options = [
        "Best Quality (Auto)",
        "1080p (Full HD)",
        "720p (HD)",
        "480p (SD)",
        "360p (Low)",
        "Audio Only (MP3)",
        "Audio Only (M4A)"
    ]
    for idx, opt in enumerate(options, 1):
        print(f"  [{idx}] {opt}")

    choice = input("\nEnter choice [1-7] (default 1): ").strip()
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(options):
            selected_format = options[choice_idx]
        else:
            selected_format = options[0]
    except ValueError:
        selected_format = options[0]

    default_folder = str(Path.home() / "Downloads")
    folder_input = input(f"\nDestination folder [{default_folder}]: ").strip()
    output_dir = folder_input if folder_input else default_folder

    os.makedirs(output_dir, exist_ok=True)
    print(f"\nDestination: {output_dir}")
    print(f"Quality:     {selected_format}")
    print(f"Playlist:    {'Yes' if download_full_playlist else 'No'}\n")

    try:
        downloader.download_media(
            url=url,
            output_folder=output_dir,
            quality=selected_format,
            download_playlist=download_full_playlist,
            progress_callback=print_progress
        )
        print("\n\nSuccess! Download finished.")
    except Exception as e:
        print(f"\n\nDownload failed: {downloader.clean_ansi(str(e))}")

def main():
    parser = argparse.ArgumentParser(description="Download YouTube videos and full playlists.")
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument("-f", "--format", default="Best Quality (Auto)",
                        choices=[
                            "Best Quality (Auto)", "1080p (Full HD)", "720p (HD)",
                            "480p (SD)", "360p (Low)", "Audio Only (MP3)", "Audio Only (M4A)"
                        ],
                        help="Video/Audio quality format")
    parser.add_argument("-o", "--output", default=str(Path.home() / "Downloads"),
                        help="Output directory path")
    parser.add_argument("--playlist", action="store_true", help="Download full playlist")

    args = parser.parse_args()

    if not args.url:
        interactive_mode()
    else:
        os.makedirs(args.output, exist_ok=True)
        print(f"URL:      {args.url}")
        print(f"Format:   {args.format}")
        print(f"Output:   {args.output}")
        print(f"Playlist: {'Yes' if args.playlist else 'No'}\n")
        try:
            downloader.download_media(
                url=args.url,
                output_folder=args.output,
                quality=args.format,
                download_playlist=args.playlist,
                progress_callback=print_progress
            )
            print("\n\nSuccess! Download finished.")
        except Exception as e:
            print(f"\n\nDownload failed: {downloader.clean_ansi(str(e))}")

if __name__ == "__main__":
    main()
