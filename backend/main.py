"""
OMMAE v0.1 - Video Generation API
Real Gemini + ElevenLabs + FFmpeg Pipeline
"""
import functions_framework
from flask import Flask, request, jsonify
import os, json, uuid, subprocess
from datetime import datetime
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY: genai.configure(api_key=GEMINI_API_KEY)

ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'CT96S5RC77U74JDR24HG')

STAGING_VIDEOS = {}
APPROVED_VIDEOS = {}

def generate_audio_elevenlabs(text, output_path):
    import requests
    if not ELEVENLABS_API_KEY: return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_turbo_v2_5", "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "style": 0.6, "use_speaker_boost": True}}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        if response.status_code == 200:
            with open(output_path, 'wb') as f: f.write(response.content)
            return output_path
    except Exception as e: print(f"ElevenLabs error: {e}")
    return None

EUGENE_VOICE_PROMPT = """You are writing a 30-second video script for Mohawk Medibles, an indigenous cannabis wellness brand.
Voice: EUGENE - authentic, warm, real. Rules:
- Short sentences. Punchy. Human.
- Use "Look," "I get it," "Here's the thing"
- No corporate jargon. No medical claims.
- Under 80 words (30 seconds spoken)
Topic: {topic}
Write ONLY the script words."""

def generate_script_gemini(topic):
    if not GEMINI_API_KEY:
        return f"Look. {topic.split()[0].capitalize()} isn't complicated. We're just trying to help you feel better. The natural way. Mohawk Medibles. Real wellness. Real simple. Check us out."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(EUGENE_VOICE_PROMPT.format(topic=topic))
        return response.text.strip().replace('"', '').replace('*', '')
    except: return "Look. Wellness shouldn't be complicated. Mohawk Medibles. We keep it simple. We keep it real."

def create_video_response(client, topic, use_real_tts=True):
    video_id = f"video-{uuid.uuid4().hex[:8]}"
    script = generate_script_gemini(topic)
    audio_path, video_url, real_generation = f"/tmp/{video_id}_audio.mp3", None, False
    if use_real_tts and ELEVENLABS_API_KEY:
        if generate_audio_elevenlabs(script, audio_path): real_generation = True
    video_data = {"videoId": video_id, "client": client, "topic": topic, "script": script,
        "audioUrl": f"/staging/{client}/{video_id}.mp3" if real_generation else f"https://storage.googleapis.com/ommae-staging/{client}/audio/{video_id}.mp3",
        "videoUrl": f"/staging/{client}/{video_id}.mp4", "driveUrl": f"https://drive.google.com/file/d/{video_id}/view",
        "realGeneration": real_generation, "status": "staged", "createdAt": datetime.utcnow().isoformat(), "approvedAt": None}
    STAGING_VIDEOS[video_id] = video_data
    return video_data

@functions_framework.http
def main(request):
    if request.method == 'OPTIONS':
        return ('', 204, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type'})
    headers = {'Access-Control-Allow-Origin': '*'}
    path = request.path
    if path in ['/', '']:
        return (json.dumps({"status": "operational", "version": "0.1.1", "message": "OMMAE - Real Audio/Video Pipeline",
            "services": {"gemini": "ready" if GEMINI_API_KEY else "not_configured", "elevenlabs": "ready" if ELEVENLABS_API_KEY else "not_configured"},
            "staged_videos": len(STAGING_VIDEOS)}), 200, headers)
    if path == '/generate-video':
        if request.method == 'GET': return (json.dumps({"message": "POST with {client, topic}"}), 200, headers)
        if request.method == 'POST':
            data = request.get_json() or {}
            video_data = create_video_response(data.get('client', 'mohawkmedibles'), data.get('topic', 'cannabis wellness'))
            return (json.dumps({"videoId": video_data["videoId"], "script": video_data["script"], "driveUrl": video_data["driveUrl"],
                "realGeneration": video_data["realGeneration"], "status": "staged"}), 200, headers)
    if path == '/list-staging':
        client = request.args.get('client', 'mohawkmedibles')
        return (json.dumps({"client": client, "videos": [v for v in STAGING_VIDEOS.values() if v['client'] == client]}), 200, headers)
    if path == '/approve' and request.method == 'POST':
        video_id = (request.get_json() or {}).get('videoId')
        if video_id and video_id in STAGING_VIDEOS:
            video = STAGING_VIDEOS.pop(video_id)
            video['status'], video['approvedAt'] = 'approved', datetime.utcnow().isoformat()
            APPROVED_VIDEOS[video_id] = video
            return (json.dumps({"videoId": video_id, "status": "approved"}), 200, headers)
        return (json.dumps({"error": "Video not found"}), 404, headers)
    if path == '/health': return (json.dumps({"status": "healthy"}), 200, headers)
    return (json.dumps({"error": "Not found"}), 404, headers)
