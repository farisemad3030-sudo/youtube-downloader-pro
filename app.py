import os
import sys
import io
import time
import threading
import urllib.request
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

import downloader

# Configure appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Video & Playlist Downloader Pro")
        self.geometry("750x880")
        self.minsize(700, 780)

        # Initialize tools
        downloader.setup_environment()

        # State Variables
        default_download_dir = str(Path.home() / "Downloads")
        self.output_dir_var = ctk.StringVar(value=default_download_dir)
        self.url_var = ctk.StringVar()
        self.format_var = ctk.StringVar(value="Best Quality (Auto)")
        self.download_playlist_var = ctk.BooleanVar(value=False)

        self.status_var = ctk.StringVar(value="Ready. Paste a link to get started.")
        self.detail_var = ctk.StringVar(value="")
        self.overall_status_var = ctk.StringVar(value="")

        self.current_media_info = None
        self.is_downloading = False
        self.cancel_requested = False
        self.thumbnail_image = None
        self.last_progress_update = 0

        self._build_ui()

    def _build_ui(self):
        self.container = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=22, pady=18)

        self._build_header()
        self._build_url_section()
        self._build_preview_section()
        self._build_settings_section()
        self._build_progress_section()
        self._build_action_bar()

    def _build_header(self):
        header = ctk.CTkFrame(self.container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        title = ctk.CTkLabel(
            header,
            text="🎬 YouTube Downloader Pro",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left")

        theme_menu = ctk.CTkOptionMenu(
            header,
            values=["Dark", "Light", "System"],
            command=self._change_theme,
            width=95,
            height=28
        )
        theme_menu.set("Dark")
        theme_menu.pack(side="right")

        subtitle = ctk.CTkLabel(
            self.container,
            text="High-speed video, audio, and full playlist downloader with Deno & FFmpeg acceleration.",
            font=ctk.CTkFont(size=13),
            text_color="gray70"
        )
        subtitle.pack(anchor="w", pady=(0, 14))

    def _build_url_section(self):
        card = ctk.CTkFrame(self.container, corner_radius=12)
        card.pack(fill="x", pady=(0, 14), ipady=6)

        title = ctk.CTkLabel(card, text="YouTube URL / Playlist Link", font=ctk.CTkFont(size=14, weight="bold"))
        title.pack(anchor="w", padx=16, pady=(6, 6))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))

        self.url_entry = ctk.CTkEntry(
            row,
            textvariable=self.url_var,
            placeholder_text="Paste YouTube video or playlist link...",
            height=38,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self.fetch_info())

        paste_btn = ctk.CTkButton(
            row,
            text="📋 Paste",
            width=75,
            height=38,
            command=self.paste_from_clipboard
        )
        paste_btn.pack(side="left", padx=(0, 6))

        clear_btn = ctk.CTkButton(
            row,
            text="✕ Clear",
            width=65,
            height=38,
            fg_color=("gray75", "#3a3a3a"),
            hover_color=("gray65", "#4a4a4a"),
            command=self.clear_input
        )
        clear_btn.pack(side="left", padx=(0, 6))

        self.fetch_btn = ctk.CTkButton(
            row,
            text="🔍 Fetch",
            width=80,
            height=38,
            fg_color="#1f538d",
            hover_color="#14375e",
            command=self.fetch_info
        )
        self.fetch_btn.pack(side="left")

    def _build_preview_section(self):
        self.preview_card = ctk.CTkFrame(self.container, corner_radius=12)
        self.preview_card.pack(fill="x", pady=(0, 14), ipady=8)

        self.preview_placeholder = ctk.CTkLabel(
            self.preview_card,
            text="📌 Paste a video or playlist link above to preview details.",
            font=ctk.CTkFont(size=13),
            text_color="gray60"
        )
        self.preview_placeholder.pack(pady=30)

        self.preview_content = ctk.CTkFrame(self.preview_card, fg_color="transparent")

        self.thumb_label = ctk.CTkLabel(self.preview_content, text="")
        self.thumb_label.pack(side="left", padx=(14, 16), pady=6)

        info_column = ctk.CTkFrame(self.preview_content, fg_color="transparent")
        info_column.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=6)

        self.info_title = ctk.CTkLabel(
            info_column,
            text="",
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=400,
            justify="left",
            anchor="w"
        )
        self.info_title.pack(fill="x", anchor="w", pady=(0, 4))

        self.info_channel = ctk.CTkLabel(
            info_column,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray75",
            anchor="w"
        )
        self.info_channel.pack(fill="x", anchor="w", pady=(0, 6))

        self.badges_row = ctk.CTkFrame(info_column, fg_color="transparent")
        self.badges_row.pack(fill="x", anchor="w")

        self.type_badge = ctk.CTkLabel(
            self.badges_row,
            text="🎥 Video",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f538d",
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.type_badge.pack(side="left", padx=(0, 8))

        self.badge_duration = ctk.CTkLabel(
            self.badges_row,
            text="⏱ --:--",
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "#2b2b2b"),
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.badge_duration.pack(side="left", padx=(0, 8))

        self.badge_views = ctk.CTkLabel(
            self.badges_row,
            text="👁 -- views",
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "#2b2b2b"),
            corner_radius=6,
            padx=8,
            pady=3
        )
        self.badge_views.pack(side="left")

    def _build_settings_section(self):
        settings_card = ctk.CTkFrame(self.container, corner_radius=12)
        settings_card.pack(fill="x", pady=(0, 14), ipady=8)

        card_title = ctk.CTkLabel(
            settings_card,
            text="Download Settings",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        card_title.pack(anchor="w", padx=16, pady=(6, 8))

        quality_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        quality_row.pack(fill="x", padx=16, pady=(0, 8))

        quality_label = ctk.CTkLabel(
            quality_row,
            text="Format / Quality:",
            font=ctk.CTkFont(size=13),
            width=130,
            anchor="w"
        )
        quality_label.pack(side="left")

        self.format_menu = ctk.CTkOptionMenu(
            quality_row,
            variable=self.format_var,
            values=[
                "Best Quality (Auto)",
                "1080p (Full HD)",
                "720p (HD)",
                "480p (SD)",
                "360p (Low)",
                "Audio Only (MP3)",
                "Audio Only (M4A)"
            ],
            height=34,
            width=220
        )
        self.format_menu.pack(side="left", fill="x", expand=True)

        folder_row = ctk.CTkFrame(settings_card, fg_color="transparent")
        folder_row.pack(fill="x", padx=16, pady=(0, 8))

        folder_label = ctk.CTkLabel(
            folder_row,
            text="Save Folder:",
            font=ctk.CTkFont(size=13),
            width=130,
            anchor="w"
        )
        folder_label.pack(side="left")

        folder_entry = ctk.CTkEntry(
            folder_row,
            textvariable=self.output_dir_var,
            height=34,
            font=ctk.CTkFont(size=12)
        )
        folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ctk.CTkButton(
            folder_row,
            text="📁 Browse",
            width=85,
            height=34,
            command=self.browse_folder
        )
        browse_btn.pack(side="left")

        # Playlist Options Container
        self.playlist_options_frame = ctk.CTkFrame(settings_card, fg_color=("gray90", "#242424"), corner_radius=8)
        self.playlist_options_frame.pack(fill="x", padx=16, pady=(4, 6), ipady=4)

        self.playlist_switch = ctk.CTkSwitch(
            self.playlist_options_frame,
            text="📑 Download entire playlist (all videos)",
            variable=self.download_playlist_var,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.playlist_switch.pack(anchor="w", padx=12, pady=(6, 2))

        self.playlist_hint_label = ctk.CTkLabel(
            self.playlist_options_frame,
            text="When enabled, videos are downloaded into a named subfolder and sequentially numbered.",
            font=ctk.CTkFont(size=11),
            text_color="gray60"
        )
        self.playlist_hint_label.pack(anchor="w", padx=12, pady=(0, 6))

    def _build_progress_section(self):
        progress_card = ctk.CTkFrame(self.container, corner_radius=12)
        progress_card.pack(fill="x", pady=(0, 14), ipady=8)

        # Overall Playlist Progress
        self.overall_frame = ctk.CTkFrame(progress_card, fg_color="transparent")
        self.overall_label = ctk.CTkLabel(
            self.overall_frame,
            textvariable=self.overall_status_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.overall_label.pack(fill="x", pady=(2, 4))

        self.overall_progress_bar = ctk.CTkProgressBar(self.overall_frame, height=10)
        self.overall_progress_bar.pack(fill="x", pady=(0, 8))
        self.overall_progress_bar.set(0)

        # Current Item Progress
        status_row = ctk.CTkFrame(progress_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(6, 4))

        self.status_label = ctk.CTkLabel(
            status_row,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.detail_label = ctk.CTkLabel(
            status_row,
            textvariable=self.detail_var,
            font=ctk.CTkFont(size=12),
            text_color="gray75",
            anchor="e"
        )
        self.detail_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(progress_card, height=12)
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 6))
        self.progress_bar.set(0)

    def _build_action_bar(self):
        action_row = ctk.CTkFrame(self.container, fg_color="transparent")
        action_row.pack(fill="x", pady=(4, 10))

        self.download_btn = ctk.CTkButton(
            action_row,
            text="⬇  Download Now",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            command=self.start_download
        )
        self.download_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.cancel_btn = ctk.CTkButton(
            action_row,
            text="⏹ Cancel",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=46,
            width=100,
            fg_color="#c62828",
            hover_color="#8e0000",
            state="disabled",
            command=self.cancel_download
        )
        self.cancel_btn.pack(side="left", padx=(0, 8))

        self.open_folder_btn = ctk.CTkButton(
            action_row,
            text="📂 Open Folder",
            font=ctk.CTkFont(size=13),
            height=46,
            width=120,
            command=self.open_downloads_folder
        )
        self.open_folder_btn.pack(side="left")

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice.lower())

    def paste_from_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_var.set(text)
                self.fetch_info()
        except Exception:
            pass

    def clear_input(self):
        self.url_var.set("")
        self.preview_content.pack_forget()
        self.preview_placeholder.pack(pady=30)
        self.status_var.set("Ready. Paste a link to get started.")
        self.detail_var.set("")
        self.overall_frame.pack_forget()
        self.download_playlist_var.set(False)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if folder:
            self.output_dir_var.set(folder)

    def open_downloads_folder(self):
        folder = self.output_dir_var.get()
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        else:
            messagebox.showwarning("Folder Not Found", f"Directory '{folder}' does not exist.")

    def fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter or paste a YouTube URL.")
            return

        self.status_var.set("Fetching information...")
        self.detail_var.set("Please wait...")
        self.fetch_btn.configure(state="disabled", text="Loading...")

        def worker():
            try:
                info = downloader.fetch_media_info(url)
                self.after(0, lambda: self._on_info_fetched(info))
            except Exception as e:
                err_msg = downloader.clean_ansi(str(e))
                self.after(0, lambda: self._on_info_error(err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_info_fetched(self, info):
        self.current_media_info = info
        self.fetch_btn.configure(state="normal", text="🔍 Fetch")
        self.status_var.set("Details loaded! Ready to download.")
        self.detail_var.set("")

        self.preview_placeholder.pack_forget()
        self.preview_content.pack(fill="x", padx=10, pady=5)

        is_playlist = info.get("is_playlist", False)
        self.info_title.configure(text=info.get("title", "Unknown Title"))
        self.info_channel.configure(text=f"👤 {info.get('uploader', 'Unknown Channel')}")

        if is_playlist:
            item_count = info.get("item_count", 0)
            self.type_badge.configure(text="📑 Playlist", fg_color="#6a1b9a")
            self.badge_duration.configure(text=f"🔢 {item_count} videos")
            self.badge_views.configure(text="Playlist")
            self.download_playlist_var.set(True)
            self.playlist_hint_label.configure(
                text=f"All {item_count} videos will be downloaded into a dedicated folder: '{info.get('title')}'"
            )
        else:
            self.type_badge.configure(text="🎥 Video", fg_color="#1f538d")
            self.badge_duration.configure(text=f"⏱ {info.get('duration', '--:--')}")
            self.badge_views.configure(text=f"👁 {info.get('views', '0')} views")
            self.download_playlist_var.set(False)

        thumb_url = info.get("thumbnail")
        if thumb_url:
            def load_thumb():
                try:
                    req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as response:
                        img_data = response.read()
                    image = Image.open(io.BytesIO(img_data))
                    image = image.resize((160, 90), Image.Resampling.LANCZOS)
                    ctk_img = ctk.CTkImage(light_image=image, dark_image=image, size=(160, 90))
                    self.after(0, lambda: self.thumb_label.configure(image=ctk_img))
                except Exception:
                    pass
            threading.Thread(target=load_thumb, daemon=True).start()

    def _on_info_error(self, err_msg):
        self.fetch_btn.configure(state="normal", text="🔍 Fetch")
        self.status_var.set("Failed to fetch media details.")
        self.detail_var.set("")
        messagebox.showerror("Error Fetching Media", f"Could not retrieve details:\n\n{err_msg}")

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.status_var.set("⏹ Cancelling download and removing partial files...")
            self.detail_var.set("Halting immediately...")
            self.cancel_btn.configure(state="disabled")

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter or paste a YouTube URL.")
            return

        folder = self.output_dir_var.get().strip()
        if not folder or not os.path.exists(folder):
            messagebox.showwarning("Invalid Folder", "Please choose a valid destination folder.")
            return

        if self.is_downloading:
            messagebox.showinfo("Busy", "A download is already in progress.")
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled", text="⏳ Downloading...")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status_var.set("Starting accelerated download...")
        self.detail_var.set("Connecting...")

        is_playlist_download = self.download_playlist_var.get()
        if is_playlist_download:
            self.overall_frame.pack(fill="x", padx=16, pady=(4, 4), before=self.status_label.master)
            self.overall_status_var.set("Playlist: Preparing items...")
            self.overall_progress_bar.set(0)
        else:
            self.overall_frame.pack_forget()

        format_choice = self.format_var.get()

        def progress_cb(data):
            if self.cancel_requested:
                return
            now = time.time()
            if now - self.last_progress_update > 0.08 or data.get("status") == "processing":
                self.last_progress_update = now
                self.after(0, lambda: self._update_download_progress(data))

        def worker():
            try:
                downloader.download_media(
                    url=url,
                    output_folder=folder,
                    quality=format_choice,
                    download_playlist=is_playlist_download,
                    progress_callback=progress_cb,
                    cancel_check=lambda: self.cancel_requested
                )
                self.after(0, self._on_download_complete)
            except downloader.DownloadCancelled:
                self.after(0, self._on_download_cancelled)
            except Exception as e:
                if self.cancel_requested:
                    self.after(0, self._on_download_cancelled)
                else:
                    err_msg = downloader.clean_ansi(str(e))
                    self.after(0, lambda: self._on_download_error(err_msg))

        threading.Thread(target=worker, daemon=True).start()

    def _update_download_progress(self, data):
        if not self.is_downloading or self.cancel_requested:
            return

        status = data.get("status")
        if status == "downloading":
            pct = data.get("percent", 0.0)
            self.progress_bar.set(max(0.0, min(1.0, pct)))

            speed = data.get("speed", "N/A")
            eta = data.get("eta", "N/A")
            pct_str = data.get("percent_str", f"{pct * 100:.1f}%")

            is_playlist = data.get("is_playlist")
            p_idx = data.get("playlist_index")
            p_total = data.get("playlist_total")
            item_title = data.get("item_title", "")

            if is_playlist and p_idx and p_total:
                overall_pct = max(0.0, min(1.0, (p_idx - 1 + pct) / p_total))
                self.overall_progress_bar.set(overall_pct)
                self.overall_status_var.set(f"Playlist: Video {p_idx} of {p_total} ({overall_pct * 100:.1f}%)")
                
                title_short = (item_title[:35] + "...") if len(item_title) > 35 else item_title
                self.status_var.set(f"[{p_idx}/{p_total}] {title_short} — {pct_str}")
            else:
                self.status_var.set(f"Downloading: {pct_str}")

            self.detail_var.set(f"Speed: {speed}  |  ETA: {eta}")

        elif status == "processing":
            self.progress_bar.set(1.0)
            is_playlist = data.get("is_playlist")
            p_idx = data.get("playlist_index")
            p_total = data.get("playlist_total")

            if is_playlist and p_idx and p_total:
                self.status_var.set(f"Video {p_idx}/{p_total}: Merging formats...")
            else:
                self.status_var.set("Finalizing & merging media formats...")
            self.detail_var.set("Please wait...")

    def _on_download_complete(self):
        self.is_downloading = False
        self.cancel_requested = False
        self.download_btn.configure(state="normal", text="⬇  Download Now")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(1.0)

        if self.download_playlist_var.get():
            self.overall_progress_bar.set(1.0)
            self.overall_status_var.set("Playlist: Complete!")

        self.status_var.set("🎉 Download completed successfully!")
        self.detail_var.set("Saved to destination folder")
        messagebox.showinfo("Success", "Download completed successfully!")

    def _on_download_cancelled(self):
        self.is_downloading = False
        self.cancel_requested = False
        self.download_btn.configure(state="normal", text="⬇  Download Now")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.overall_progress_bar.set(0)
        self.status_var.set("⏹ Download cancelled. Incomplete partial files deleted.")
        self.detail_var.set("Ready")

    def _on_download_error(self, err_msg):
        self.is_downloading = False
        self.cancel_requested = False
        self.download_btn.configure(state="normal", text="⬇  Download Now")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_var.set("Download failed.")
        self.detail_var.set("")
        messagebox.showerror("Download Error", f"An error occurred while downloading:\n\n{err_msg}")

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
