import re
import requests
import base64
import wave
import os
import shutil

# --- CONFIGURATION ---
# PLEASE FILL IN YOUR API KEY AND THE VOICE NAMES FOR THE CHARacters
API_KEY = "sk-GsbjtPUeDrJzI5Q58JTDwg"
VOICES = {
    "Chuyên gia Lan": "achernar", # A calm, warm, male voice for the expert
    "bà Nhung": "gacrux"     # An emotional, elderly male voice
}
SCRIPT_FILE = "script.txt"
OUTPUT_FILE = "podcast_output.wav" # Outputting as WAV first
TEMP_DIR = "temp_audio_chunks"
API_URL = "https://api.thucchien.ai/gemini/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"

# --- Helper Functions ---

def parse_script(file_path):
    """Parses the script file to extract dialogue and speakers."""
    dialogues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: The script file was not found at '{file_path}'")
        return None

    dialogue_pattern = re.compile(r'^\*   \*\*Lời thoại \((Chuyên gia lan|Bà Nhung)\):\*\* (.*)')
    for line in lines:
        match = dialogue_pattern.match(line)
        if match:
            speaker = match.group(1).strip()
            dialogue_text = match.group(2).strip()
            
            cleaned_dialogue = re.sub(r'^\(.*\)\s*', '', dialogue_text)
            
            if cleaned_dialogue:
                 dialogues.append({"speaker": speaker, "text": cleaned_dialogue})
        
    return dialogues

def generate_audio_chunk(text, voice_name, output_path):
    """Calls the TTS API and saves the audio chunk as a WAV file."""
    # Ensure the output directory exists right before writing.
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    headers = {
        'x-goog-api-key': API_KEY,
        'Content-Type': 'application/json',
    }
    json_data = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice_name}
                }
            }
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=json_data)
        response.raise_for_status()
        
        response_json = response.json()
        audio_data_base64 = response_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
        audio_data = base64.b64decode(audio_data_base64)
        
        # Save as a WAV file
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(24000) # 24kHz sample rate
            wf.writeframes(audio_data)
        return True

    except requests.exceptions.RequestException as e:
        print(f"Error calling API for text '{text[:50]}...': {e}")
        if e.response is not None:
             print(f"Response content: {e.response.text}")
        return False
    except (KeyError, IndexError) as e:
        print(f"Error parsing API response: {e}")
        print(f"Response content: {response.text}")
        return False

def combine_wav_files(input_files, output_path):
    """Combines multiple WAV files into a single WAV file."""
    if not input_files:
        print("No input files to combine.")
        return

    outfile = None
    try:
        outfile = wave.open(output_path, 'wb')
        
        # Use parameters from the first file
        with wave.open(input_files[0], 'rb') as infile:
            outfile.setparams(infile.getparams())

        # Write data from each file
        for file_path in input_files:
            with wave.open(file_path, 'rb') as infile:
                outfile.writeframes(infile.readframes(infile.getnframes()))
    except Exception as e:
        print(f"Error combining WAV files: {e}")
    finally:
        if outfile:
            outfile.close()

# --- Main Script ---

def main():
    """Main function to generate the podcast audio."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    print(f"Parsing script from '{SCRIPT_FILE}'...")
    dialogues = parse_script(SCRIPT_FILE)
    
    if not dialogues:
        print("No dialogues were found. Please check the script file format and path.")
        return

    print(f"Found {len(dialogues)} lines of dialogue.")
    
    audio_files = []
    # Add initial silence
    silence_path = os.path.join(TEMP_DIR, "silence_start.wav")
    with wave.open(silence_path, 'wb') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
        wf.writeframes(b'\x00' * 24000) # 0.5s silence
    audio_files.append(silence_path)

    for i, dialogue in enumerate(dialogues):
        speaker = dialogue['speaker']
        text = dialogue['text']
        voice_name = VOICES.get(speaker)
        
        if not voice_name:
            print(f"Warning: No voice configured for speaker '{speaker}'. Skipping this line.")
            continue
            
        print(f"[{i+1}/{len(dialogues)}] Generating audio for '{speaker}': '{text[:60]}...'")
        
        chunk_path = os.path.join(TEMP_DIR, f"chunk_{i}.wav")
        if generate_audio_chunk(text, voice_name, chunk_path):
            audio_files.append(chunk_path)
            # Add a short pause after each line
            silence_path = os.path.join(TEMP_DIR, f"silence_{i}.wav")
            with wave.open(silence_path, 'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
                wf.writeframes(b'\x00' * 36000) # 0.75s silence
            audio_files.append(silence_path)

    print(f"\nCombining {len(audio_files)} audio chunks into '{OUTPUT_FILE}'...")
    combine_wav_files(audio_files, OUTPUT_FILE)
    
    print("Cleaning up temporary files...")
    shutil.rmtree(TEMP_DIR)

    print("Done!")
    print(f"Your podcast audio has been saved as {os.path.abspath(OUTPUT_FILE)}")
    print("Note: The output is a WAV file. You may need to convert it to MP3 using another tool if required.")


if __name__ == "__main__":
    main()
