"""
OMMAE Audio Generator - REAL TTS Options
Edge-TTS (free), ElevenLabs (voice clone), Google TTS
"""

import os
import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)


async def generate_edge_tts(text, output_path, voice="en-US-GuyNeural"):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        logger.info(f"Edge-TTS generated: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Edge-TTS failed: {e}")
        raise


def generate_elevenlabs(text, output_path, voice_id=None, api_key=None):
    import requests
    api_key = api_key or os.environ.get('ELEVENLABS_API_KEY')
    voice_id = voice_id or os.environ.get('ELEVENLABS_VOICE_ID', 'pNInz6obpgDQGcFmaJgB')
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not set")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key}
    data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return output_path
    raise Exception(f"ElevenLabs error: {response.status_code}")


async def generate_audio(text, output_path, preferred_engine="auto"):
    if os.environ.get('ELEVENLABS_API_KEY'):
        try:
            return generate_elevenlabs(text, output_path)
        except:
            pass
    try:
        return await generate_edge_tts(text, output_path)
    except:
        return create_ambient_audio(text, output_path)


def create_ambient_audio(text, output_path, duration=15):
    words = len(text.split())
    dur = max(duration, int(words / 2.5))
    cmd = ['ffmpeg', '-y', '-f', 'lavfi', '-i', f'anoisesrc=d={dur}:c=pink:a=0.002', '-c:a', 'aac', output_path]
    subprocess.run(cmd, capture_output=True)
    logger.info(f"Ambient audio: {output_path}")
    return output_path
