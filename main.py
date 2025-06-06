import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from demucs_runner import run_demucs
from downloader import youtube_audio_download
from settings import DEFAULT_OUTPUT_DIR
import threading
import os
import webbrowser
import sys
import itertools

# 실행 파일 경로 설정
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ffmpeg 경로 설정
FFMPEG_PATH = os.path.join(BASE_DIR, 'ffmpeg.exe')

# demucs 모델 경로 설정
DEMUCS_MODEL_PATH = os.path.join(BASE_DIR, 'models')

# 애니메이션용 이모지 리스트
ANIMATION_FRAMES = ["🐱", "🐾", "😺", "😸", "😻", "🐾"]
# 전역 변수로 선언
animation_cycle = None
animation_running = False

def animate_progress():
    global animation_running, animation_cycle
    if animation_running:
        frame = next(animation_cycle)
        progress_label.config(text=f"변환중... {frame}")
        progress_label.after(300, animate_progress)

def update_progress(percent):
    global animation_running, animation_cycle
    if percent == 0 or percent == 100:
        animation_running = False
        progress_label.config(text="")
    else:
        if not animation_running:
            animation_running = True
            animation_cycle = itertools.cycle(ANIMATION_FRAMES)
            animate_progress()

def run_separation():
    input_path = file_path.get()
    youtube_url = url_entry.get()
    output_dir = os.path.join(BASE_DIR, 'outputs')
    option = option_var.get()

    if not input_path and not youtube_url:
        messagebox.showerror("오류", "파일을 선택하거나 유튜브 링크를 입력하세요.")
        return
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    if youtube_url:
        messagebox.showinfo("알림", "유튜브에서 오디오를 다운로드합니다...")
        input_path = youtube_audio_download(youtube_url, output_dir)
        input_path = os.path.abspath(os.path.normpath(input_path))
        print("demucs에 넘길 파일 경로:", input_path)
        print("존재 여부:", os.path.exists(input_path))
        if not os.path.exists(input_path):
            messagebox.showerror("오류", f"유튜브 다운로드 실패!\n{input_path} 파일이 존재하지 않습니다.")
            return
        # 유튜브 제목 기반으로 track_name 추출
        track_name = os.path.splitext(os.path.basename(input_path))[0]
    else:
        track_name = os.path.splitext(os.path.basename(input_path))[0]

    result_folder, err = run_demucs(input_path, output_dir, option, progress_callback=update_progress, track_name=track_name)
    if err:
        messagebox.showerror("분리 실패", err)
    else:
        messagebox.showinfo("분리 완료", f"결과 폴더: {result_folder}")
        try:
            os.startfile(result_folder)
        except Exception as e:
            print(f"폴더 자동 열기 실패: {e}")

def browse_file():
    filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
    if filename:
        file_path.set(filename)

def browse_output():
    folder = filedialog.askdirectory()
    if folder:
        output_path.set(folder)

def open_youtube():
    webbrowser.open("https://www.youtube.com/")

root = tk.Tk()
root.title("날둥이의 연습 도우미: 음원 분리 마법")
root.geometry("700x480")
root.configure(bg="#f7f7fa")

TITLE_FONT = ("Arial", 22, "bold")
LABEL_FONT = ("Arial", 14)
ENTRY_FONT = ("Arial", 13)
BUTTON_FONT = ("Arial", 12, "bold")

file_path = tk.StringVar()
output_path = tk.StringVar()
option_var = tk.StringVar(value="전체 분리")
progress_var = tk.IntVar(value=0)

# 타이틀
frame0 = tk.Frame(root, bg="#f7f7fa")
frame0.pack(pady=18)
tk.Label(frame0, text="날둥이의 연습 도우미: 음원 분리 마법", font=TITLE_FONT, bg="#f7f7fa", fg="#2d2d2d").pack()

# 변환중 라벨 (중앙, 크게)
progress_label = tk.Label(root, text="", font=("Arial", 18, "bold"), bg="#f7f7fa", fg="#4f8cff")
progress_label.pack(pady=30)

# 파일/유튜브 입력
frame1 = tk.Frame(root, bg="#f7f7fa")
frame1.pack(pady=10, fill="x", padx=30)
tk.Label(frame1, text="1. 파일 선택", font=LABEL_FONT, bg="#f7f7fa").grid(row=0, column=0, sticky="w")
tk.Entry(frame1, textvariable=file_path, width=38, font=ENTRY_FONT).grid(row=0, column=1, padx=5)
tk.Button(frame1, text="파일 선택", command=browse_file, font=BUTTON_FONT, bg="#e0e7ff").grid(row=0, column=2, padx=5)

# 유튜브 입력 (파일 선택 아래쪽)
frame1b = tk.Frame(root, bg="#f7f7fa")
frame1b.pack(pady=2, fill="x", padx=30)
tk.Label(frame1b, text="2. 유튜브 링크", font=LABEL_FONT, bg="#f7f7fa").grid(row=0, column=0, sticky="w")
url_entry = tk.Entry(frame1b, width=38, font=ENTRY_FONT)
url_entry.grid(row=0, column=1, padx=5)
tk.Button(frame1b, text="유튜브 바로가기", command=open_youtube, font=BUTTON_FONT, bg="#ffebc6").grid(row=0, column=2, padx=5)

# 옵션 선택
frame2 = tk.Frame(root, bg="#f7f7fa")
frame2.pack(pady=18, fill="x", padx=30)
tk.Label(frame2, text="3. 분리 옵션 선택", font=LABEL_FONT, bg="#f7f7fa").pack(anchor="w")
option_menu = ttk.Combobox(frame2, textvariable=option_var, font=ENTRY_FONT, width=30, state="readonly")
option_menu['values'] = ("전체 분리", "보컬", "드럼", "베이스", "기타", "모든 음원")
option_menu.pack(pady=5, anchor="w")

# 결과 폴더
frame3 = tk.Frame(root, bg="#f7f7fa")
frame3.pack(pady=10, fill="x", padx=30)
tk.Label(frame3, text="4. 결과 저장 폴더", font=LABEL_FONT, bg="#f7f7fa").grid(row=0, column=0, sticky="w")
tk.Entry(frame3, textvariable=output_path, width=38, font=ENTRY_FONT).grid(row=0, column=1, padx=5)
tk.Button(frame3, text="폴더 선택", command=browse_output, font=BUTTON_FONT, bg="#e0e7ff").grid(row=0, column=2, padx=5)

# 실행/종료 버튼
frame4 = tk.Frame(root, bg="#f7f7fa")
frame4.pack(pady=10)
tk.Button(frame4, text="실행", command=lambda: threading.Thread(target=run_separation, daemon=True).start(), font=BUTTON_FONT, bg="#4f8cff", fg="white", width=12, height=2).pack(side="left", padx=20)
tk.Button(frame4, text="종료", command=root.quit, font=BUTTON_FONT, bg="#ffb4b4", fg="black", width=12, height=2).pack(side="left", padx=20)

# GUI 하단에 책임소재 안내문구 추가
footer_label = tk.Label(root, text="※ 본 프로그램은 음원 저작권 및 사용에 대한 책임을 지지 않습니다.", font=("Arial", 10), bg="#f7f7fa", fg="#888888")
footer_label.pack(side="bottom", pady=8)

root.mainloop() 