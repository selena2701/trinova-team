import os
import math
import re
from dotenv import load_dotenv
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

# Assuming the services and output_manager are in the same directory or in python path
from services.base import ServiceConfig
from services.image_service_enhanced import EnhancedImageService
from services.tts_service import TTSService
from services.video_service import VeoVideoService
from output_manager import OutputManager


def parse_segments(script):
    """Parses the script to extract segments with visual and dialogue information."""
    pattern = r'\[Segment (\d+).*?\]\s*Visual:\s*(.*?)\s*Dialogue:\s*(.*?)(?=\[Segment|\Z)'
    matches = re.findall(pattern, script, re.DOTALL)
    return {
        int(m[0]): {"visual": m[1].strip(), "dialogue": m[2].strip()} for m in matches
    }


def solve(output_mgr: OutputManager) -> str:
    """
    Main function to generate the Vietnamese video podcast.
    """
    load_dotenv()
    config = ServiceConfig()
    image_service = EnhancedImageService(config)
    tts_service = TTSService(config)
    video_service = VeoVideoService(config)

    # --- USER INPUTS ---
    TOTAL_DURATION = 240  # seconds
    SCRIPT_FILE_PATH = "script.txt"
    CHARACTER_DESCRIPTIONS = {
        "nguoi_cao_tuoi": "Vietnamese old person, portrait",
        "chuyen_gia": "Vietnamese consultant, portrait",
    }
    VOICE_MAP = {
        "nguoi_cao_tuoi": "Vietnamese-Male-Old",
        "chuyen_gia": "Vietnamese-Male-Young",
    }
    BACKGROUND_DESCRIPTION = "Vietnamese studio podcast background"
    GIF_OVERLAY_PATH = "image_ref/diaThan.gif"

    # --- SETUP ---
    NUM_SEGMENTS = math.ceil(TOTAL_DURATION / 8)
    folder = output_mgr.create_solution_folder(1, "Vietnamese Video")
    os.makedirs(f"{folder}/reference", exist_ok=True)
    os.makedirs(f"{folder}/intermediate", exist_ok=True)

    if not os.path.exists(SCRIPT_FILE_PATH):
        raise FileNotFoundError(f"Script file not found: {SCRIPT_FILE_PATH}")
    if not os.path.exists(GIF_OVERLAY_PATH):
        raise FileNotFoundError(f"GIF overlay not found: {GIF_OVERLAY_PATH}")

    # --- STEP 0: Generate Character and Background References ---
    VIETNAMESE_CHAR_STYLE = """Vietnamese person, Southeast Asian features, warm tan skin,
    almond eyes, straight black hair, Vietnamese styling, red #DA251D/gold #FFCD00,
    bình dị style, soft lighting, 1920x1080, portrait, NO TEXT"""

    char_refs = {}
    for name, desc in CHARACTER_DESCRIPTIONS.items():
        ref_prompt = f"{VIETNAMESE_CHAR_STYLE}\n{desc}\nReference portrait"
        ref_path = f"{folder}/reference/character_{name}.png"
        image_service.generate_and_save_chat(ref_prompt, ref_path)
        char_refs[name] = ref_path
        print(f"Generated character reference: {ref_path}")

    background_prompt = f"Vietnamese studio podcast background, warm lighting, professional, 1920x1080, NO TEXT\n{BACKGROUND_DESCRIPTION}"
    background_ref_path = f"{folder}/reference/background.png"
    image_service.generate_and_save_chat(background_prompt, background_ref_path)
    print(f"Generated background reference: {background_ref_path}")

    # --- STEP 1: Load Script ---
    with open(SCRIPT_FILE_PATH, "r", encoding="utf-8") as f:
        script_content = f.read()
    segments = parse_segments(script_content)

    # --- STEP 2: Generate Audio ---
    audio_paths = {}  # Use a dictionary to map segment index to audio path
    for i in range(1, NUM_SEGMENTS + 1):
        segment = segments.get(i, {})
        dialogue = segment.get("dialogue", "")
        visual_desc = segment.get("visual", "")

        voice_name = VOICE_MAP.get("chuyen_gia")  # Default voice
        if "nguoi_cao_tuoi" in visual_desc:
            voice_name = VOICE_MAP.get("nguoi_cao_tuoi")

        if dialogue:
            print(f"Synthesizing audio for segment {i}...")
            audio_bytes = tts_service.synthesize(dialogue, voice_name=voice_name)
            audio_path = f"{folder}/intermediate/audio_{i}.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            audio_paths[i] = audio_path

    # --- STEP 3: Generate Video from Static Image + Add Audio ---
    video_paths = []
    for i in range(1, NUM_SEGMENTS + 1):
        segment = segments.get(i, {})
        visual_desc = segment.get("visual", "")
        
        image_path = background_ref_path
        if "nguoi_cao_tuoi" in visual_desc:
            image_path = char_refs["nguoi_cao_tuoi"]
        elif "chuyen_gia" in visual_desc:
            image_path = char_refs["chuyen_gia"]

        video_with_audio = None
        duration = 8  # Default duration for silent clips

        audio_path = audio_paths.get(i)
        if audio_path:
            try:
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                print(f"Creating video for segment {i} with audio...")
                image_clip = ImageClip(image_path).set_duration(duration)
                video_with_audio = image_clip.set_audio(audio_clip)
            except Exception as e:
                print(f"Error processing audio for segment {i}: {e}")
                # Fallback to silent clip
                image_clip = ImageClip(image_path).set_duration(duration)
                video_with_audio = image_clip.set_audio(None)
        else:
            # Create a silent video clip
            print(f"Creating silent video for segment {i}...")
            image_clip = ImageClip(image_path).set_duration(duration)
            video_with_audio = image_clip

        if video_with_audio:
            video_path = f"{folder}/intermediate/video_{i}.mp4"
            video_with_audio.write_videofile(video_path, codec="libx264", fps=24)
            video_paths.append(video_path)
            # Clean up clips
            if 'audio_clip' in locals() and audio_clip:
                audio_clip.close()
            if 'image_clip' in locals() and image_clip:
                image_clip.close()


    # --- STEP 4: Concatenate and Overlay GIF ---
    print("Concatenating video clips...")
    if not video_paths:
        raise ValueError("No video clips were generated to concatenate.")
        
    clips = [VideoFileClip(p) for p in video_paths]
    final_video = concatenate_videoclips(clips, method="compose")

    print("Overlaying GIF...")
    gif_clip = (
        VideoFileClip(GIF_OVERLAY_PATH, has_mask=True)
        .set_loop(True)
        .resize(height=int(final_video.h * 0.15))  # 15% of video height
        .set_position(("left", "top"))
        .set_duration(final_video.duration)
    )

    final_composite = CompositeVideoClip([final_video, gif_clip])

    output_path = f"{folder}/output_final.mp4"
    print(f"Writing final video to {output_path}...")
    final_composite.write_videofile(output_path, codec="libx264", fps=30)

    # --- CLEANUP ---
    for c in clips:
        c.close()
    final_video.close()
    gif_clip.close()
    final_composite.close()

    # --- SAVE METADATA ---
    final_path = output_mgr.save_final_file(output_path, 1, "Video", "video")
    output_mgr.save_metadata(final_path, 1, "Video", "video")
    
    print(f"Successfully generated video: {final_path}")
    return final_path
