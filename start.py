import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment
import pygame
import time
from mutagen.mp3 import MP3

class LRCGenerator:
    def __init__(self, master):
        self.master = master
        self.master.title("LRC Generator")
        self.master.geometry("600x400")

        self.folder_path = ""
        self.before_folder_path = ""
        self.music_path = ""
        self.lyric_path = ""
        self.lyrics = []
        self.current_line = 1
        self.playing = False
        self.playback_speed = 1.0
        self.audio = None
        self.audio_length = 0
        self.start_time = 0
        self.pause_time = 0
        self.loaded = False

        self.setup_ui()

    def setup_ui(self):
        self.folder_btn = tk.Button(self.master, text="フォルダ選択", command=self.select_folder)
        self.folder_btn.pack(pady=10)

        self.lyrics_text = tk.Text(self.master, height=10, width=50)
        self.lyrics_text.pack(pady=10)

        self.controls_frame = tk.Frame(self.master)
        self.controls_frame.pack(pady=10)

        self.play_btn = tk.Button(self.controls_frame, text="再生/一時停止", command=self.toggle_play)
        self.play_btn.grid(row=0, column=0, padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = tk.Scale(self.master, variable=self.progress_var, from_=0, to=100, orient=tk.HORIZONTAL, length=500, showvalue=0, command=self.seek)
        self.progress_bar.pack(pady=10)

        self.save_btn = tk.Button(self.master, text="LRC保存", command=self.save_lrc)
        self.save_btn.pack(pady=10)

        self.master.bind('<k>', self.add_timestamp)
        self.master.bind('<j>', self.undo_timestamp)

    def select_folder(self):
        self.folder_path = filedialog.askdirectory()
        if self.folder_path and self.folder_path != self.before_folder_path:
            self.loaded = False
            self.music_path = os.path.join(self.folder_path, "music.mp3")
            self.lyric_path = os.path.join(self.folder_path, "lyric.txt")

            if not os.path.exists(self.music_path) or not os.path.exists(self.lyric_path):
                messagebox.showerror("エラー", "music.mp3 または lyric.txt がフォルダ内に見つかりません。")
                return

            self.init_audio()
            self.load_lyrics()
            self.loaded = True
            self.current_line = 1
            self.before_folder_path = self.folder_path


    def load_lyrics(self):
        try:
            with open(self.lyric_path, 'r', encoding='utf-8') as f:
                lyrics = f.readlines()

            if lyrics and not lyrics[0] == '\n':
                lyrics.insert(0, '[00:00.00]\n')
            if lyrics and not lyrics[-1].endswith('\n'):
                lyrics[-1] += '\n'
            if lyrics and not lyrics[-1] == '\n':
                lyrics.append('\n')

            self.lyrics = lyrics
            self.seek(0)
            self.update_lyrics_display()
        except Exception as e:
            messagebox.showerror("エラー", f"歌詞ファイルの読み込みに失敗しました: {str(e)}")

    def init_audio(self):
        try:
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.music.load(self.music_path)
            self.audio = MP3(self.music_path)
            self.audio_length = self.audio.info.length
        except pygame.error as e:
            messagebox.showerror("エラー", f"Pygameのミキサー初期化に失敗しました: {str(e)}")
        except Exception as e:
            messagebox.showerror("エラー", f"音楽ファイルの読み込みに失敗しました: {str(e)}")

    def update_lyrics_display(self):
        self.lyrics_text.delete(1.0, tk.END)
        for i, line in enumerate(self.lyrics):
            if i == self.current_line:
                self.lyrics_text.insert(tk.END, f"> {line}")
            else:
                self.lyrics_text.insert(tk.END, line)
        self.lyrics_text.see(f"{self.current_line + 1}.0")

    def toggle_play(self):
        if not self.playing:
            if self.pause_time:
                self.start_time = time.time() - self.pause_time
            else:
                self.start_time = time.time()
            pygame.mixer.music.play(start=self.pause_time)
            self.playing = True
            self.update_progress()
        else:
            self.pause_time = time.time() - self.start_time
            pygame.mixer.music.pause()
            self.playing = False

    def seek(self, value):
        pos = float(value) / 100 * self.audio_length
        self.start_time = time.time() - pos
        self.pause_time = pos
        pygame.mixer.music.play(start=pos)
        if not self.playing:
            pygame.mixer.music.pause()

    def update_progress(self):
        if self.playing:
            current_time = time.time() - self.start_time
            self.progress_var.set((current_time / self.audio_length) * 100)
            self.master.after(100, self.update_progress)

    def get_current_time(self):
        if self.playing:
            return time.time() - self.start_time
        else:
            return self.pause_time

    def add_timestamp(self, event):
        current_time = self.get_current_time()
        timestamp = time.strftime("[%M:%S.", time.gmtime(current_time)) + f"{int(current_time * 1000 % 1000):03d}]"
        self.lyrics[self.current_line] = timestamp + self.lyrics[self.current_line].lstrip('[')
        self.current_line += 1
        self.update_lyrics_display()

    def undo_timestamp(self, event):
        if self.current_line > 0:
            self.current_line -= 1
            prev_timestamp = self.lyrics[self.current_line].split(']')[0][1:]
            self.lyrics[self.current_line] = self.lyrics[self.current_line].split(']', 1)[-1]
            self.update_lyrics_display()
            if self.current_line > 0:
                minutes, seconds = map(float, prev_timestamp.split(':'))
                seek_time = max(0, (minutes * 60 + seconds) - 3)
                self.start_time = time.time() - seek_time
                self.pause_time = seek_time
                pygame.mixer.music.play(start=seek_time)
                if not self.playing:
                    pygame.mixer.music.pause()

    def save_lrc(self):
        if not self.folder_path:
            messagebox.showerror("エラー", "フォルダを選択してください。")
            return

        lrc_path = os.path.join(self.folder_path, "time.txt")
        if not lrc_path:
            return

        try:
            with open(lrc_path, 'w', encoding='utf-8') as f:
                for line in self.lyrics:
                    f.write(line)
            messagebox.showinfo("成功", f"LRCファイルが保存されました: {lrc_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"LRCファイルの保存に失敗しました: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LRCGenerator(root)
    root.mainloop()
