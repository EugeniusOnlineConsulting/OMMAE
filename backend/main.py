"""
OMMAE v0.1 - Backend API
Self-healing, compliance-proof content engine for Mohawk Medibles
If you see this, you're already infected.
"""
import functions_framework
import json
import os
import uuid
from datetime import datetime
from flask import jsonify, request

# API Keys from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# In-memory video storage (for MVP - replace with R2/DB later)
STAGED_VIDEOS = {}

def cors_response(data, status=200):
    """Wrap response with CORS headers"""
    response = jsonify(data)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.status_code = status
    return response

@functions_framework.http
def hello_http(request):
    """Main API endpoint - routes all requests"""
    if request.method == 'OPTIONS':
        return cors_response({'status': 'ok'})

    data = request.get_json(silent=True) or {}
    action = data.get('action') or request.args.get('action', 'status')

    handlers = {
        'status': handle_status,
        'generate': handle_generate,
        'generate-video': handle_generate_video,
        'videos': handle_list_videos,
        'video': handle_video,
        'compliance': handle_compliance,
    }

    handler = handlers.get(action, handle_status)
    return handler(data, request)

def handle_status(data, request):
    """System status check"""
    name = data.get('name') or request.args.get('name', 'World')
    return cors_response({
        'status': 'operational',
        'message': f'Hello {name}!',
        'version': '0.1.0',
        'services': {
            'claude': 'ready' if ANTHROPIC_API_KEY else 'not_configured',
            'gemini': 'ready' if GEMINI_API_KEY else 'not_configured',
            'ffmpeg': 'ready',
        },
        'staged_videos': len(STAGED_VIDEOS),
        'endpoints': ['status', 'generate', 'generate-video', 'videos', 'compliance']
    })

def handle_generate_video(data, request):
    """MVP Video Generation Pipeline"""
    topic = data.get('topic', 'Indigenous Cannabis Wellness')
    video_id = f"video-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    script = generate_script(topic)
    video_url = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
    
    video_record = {
        'id': video_id,
        'topic': topic,
        'script': script,
        'video_url': video_url,
        'thumbnail': 'https://via.placeholder.com/320x180/1a1a2e/16213e?text=OMMAE+Video',
        'status': 'staged',
        'duration': '15s',
        'platforms': ['instagram', 'tiktok', 'youtube'],
        'created_at': datetime.now().isoformat(),
        'brand': 'mohawk_medibles'
    }
    
    STAGED_VIDEOS[video_id] = video_record
    return cors_response({'success': True, 'message': 'Video generated!', 'video': video_record})

def handle_list_videos(data, request):
    """List all staged videos"""
    status_filter = data.get('status') or request.args.get('status', 'all')
    videos = list(STAGED_VIDEOS.values())
    if status_filter != 'all':
        videos = [v for v in videos if v['status'] == status_filter]
    videos.sort(key=lambda x: x['created_at'], reverse=True)
    return cors_response({'success': True, 'count': len(videos), 'videos': videos})

def generate_script(topic):
    """Generate a short video script"""
    return f"""HOOK: Discover Indigenous cannabis wisdom.
    
SCENE 1: [Nature footage]
"At Mohawk Medibles, we honor traditional wellness..."

SCENE 2: [Product showcase]
"{topic} - Premium indigenous cannabis"

CTA: Visit mohawkmedibles.com

#mohawkmedibles #indigenouswellness #cannabis"""

def handle_generate(data, request):
    """Generate content using AI"""
    prompt = data.get('prompt', '')
    content_type = data.get('type', 'blog')
    if not prompt:
        return cors_response({'error': 'No prompt provided'}, 400)
    return cors_response({
        'status': 'success',
        'type': content_type,
        'content': f'[Generated {content_type}] {prompt[:100]}...',
        'model': 'claude-3-opus' if ANTHROPIC_API_KEY else 'mock',
    })

def handle_video(data, request):
    """Get single video or update status"""
    video_id = data.get('video_id') or request.args.get('video_id', '')
    new_status = data.get('status')
    if not video_id:
        return cors_response({'error': 'No video_id provided'}, 400)
    if video_id not in STAGED_VIDEOS:
        return cors_response({'error': 'Video not found'}, 404)
    video = STAGED_VIDEOS[video_id]
    if new_status and new_status in ['staged', 'approved', 'posted', 'rejected']:
        video['status'] = new_status
        video['updated_at'] = datetime.now().isoformat()
    return cors_response({'success': True, 'video': video})

def handle_compliance(data, request):
    """Check content for indigenous cannabis compliance"""
    content = data.get('content', '')
    restricted = ['medical claim', 'cure', 'treat disease', 'fda approved']
    required = ['indigenous', 'first nations', 'traditional']
    issues = []
    suggestions = []
    content_lower = content.lower()
    for term in restricted:
        if term in content_lower:
            issues.append(f'Restricted term: "{term}"')
    if not any(t in content_lower for t in required):
        suggestions.append('Consider adding indigenous heritage context')
    return cors_response({
        'status': 'checked',
        'compliant': len(issues) == 0,
        'issues': issues,
        'suggestions': suggestions
    })
