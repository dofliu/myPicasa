import sys
print(f"腳本執行的 Python 解譯器路徑: {sys.executable}")
print(f"Python 版本: {sys.version}")
print(f"Python 模組搜尋路徑 (sys.path):")
for p in sys.path:
    print(f"  - {p}")

import os
from moviepy import VideoFileClip, concatenate_videoclips # type: ignore
from natsort import natsorted # For natural sorting of filenames
def merge_videos_from_folder(folder_path, output_filename, video_extensions=None):
    """
    Merges multiple video files from a specified folder into a single video file.

    Args:
        folder_path (str): The path to the folder containing the video files.
        output_filename (str): The name (including path if necessary) for the output merged video file.
        video_extensions (list, optional): A list of video file extensions to consider.
                                           Defaults to ['.mp4', '.avi', '.mov', '.mkv'].
    """
    if video_extensions is None:
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']

    video_files = []
    try:
        for filename in os.listdir(folder_path):
            if any(filename.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(folder_path, filename))
    except FileNotFoundError:
        print(f"錯誤：找不到資料夾 '{folder_path}'。請檢查路徑是否正確。")
        return
    except Exception as e:
        print(f"讀取資料夾 '{folder_path}' 時發生錯誤：{e}")
        return

    if not video_files:
        print(f"在資料夾 '{folder_path}' 中沒有找到任何支援的影片檔案。")
        print(f"支援的副檔名為：{', '.join(video_extensions)}")
        return

    # 使用 natsorted 進行自然排序，確保檔案順序符合預期 (例如 video1.mp4, video2.mp4, video10.mp4)
    video_files = natsorted(video_files)

    print("將合併以下影片檔案 (依此順序)：")
    for vf in video_files:
        print(f" - {os.path.basename(vf)}")

    clips = []
    for video_file in video_files:
        try:
            clip = VideoFileClip(video_file)
            clips.append(clip)
        except Exception as e:
            print(f"警告：讀取影片 '{video_file}' 時發生錯誤，將跳過此檔案：{e}")
            # 確保即使發生錯誤，之前成功載入的 clip 也被關閉
            for loaded_clip in clips:
                loaded_clip.close() # 釋放資源
            return # 或者選擇 continue 跳過這個檔案，但要小心 clips 列表

    if not clips:
        print("沒有任何影片可以成功載入並合併。")
        return

    try:
        print(f"\n開始合併影片...")
        final_clip = concatenate_videoclips(clips, method="compose") # "compose" 通常效果較好
        final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
        print(f"\n影片成功合併並儲存為 '{output_filename}'")
    except Exception as e:
        print(f"合併影片或寫入檔案時發生錯誤：{e}")
    finally:
        # 確保所有 clip 都被關閉以釋放資源
        for clip in clips:
            clip.close()
        if 'final_clip' in locals() and final_clip:
            final_clip.close()

if __name__ == "__main__":
    # --- 使用者設定 ---
    input_folder = "videos_to_merge"  # 請將此路徑替換成你的影片資料夾路徑
    output_video_file = "merged_video.mp4" # 合併後的影片檔案名稱與路徑
    # --------------------

    # 建立一個範例資料夾 (如果它不存在)
    if not os.path.exists(input_folder):
        os.makedirs(input_folder)
        print(f"已建立範例資料夾 '{input_folder}'. 請將你的影片檔案放入此資料夾中。")
        print("然後再次執行此腳本。")
    else:
        if not os.listdir(input_folder):
             print(f"資料夾 '{input_folder}' 是空的。請將你的影片檔案放入此資料夾中。")
        else:
            merge_videos_from_folder(input_folder, output_video_file)

    # 範例：如果你想指定不同的副檔名
    # custom_extensions = ['.mp4', '.mkv']
    # merge_videos_from_folder("path/to/your/videos", "custom_merged.mp4", video_extensions=custom_extensions)
