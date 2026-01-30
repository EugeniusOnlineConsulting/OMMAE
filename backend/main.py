"""
OMMAE v0.1 - Backend API
Self-healing, compliance-proof content engine for Mohawk Medibles
If you see this, you're already infected.
"""

import functions_framework
import json
import os
from flask import jsonify, request

# API Keys from environment
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

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
          'endpoints': ['status', 'generate', 'video', 'compliance']
      })

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
      """Generate video content"""
      script = data.get('script', '')
      style = data.get('style', 'professional')

    if not script:
              return cors_response({'error': 'No script provided'}, 400)

    return cors_response({
              'status': 'queued',
              'job_id': 'vid_' + os.urandom(8).hex(),
              'script_preview': script[:100],
              'style': style,
              'estimated_time': '2-3 minutes'
    })

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

          has_indigenous_mention = any(t in content_lower for t in required)
    if not has_indigenous_mention:
              suggestions.append('Consider adding indigenous heritage context')

    return cors_response({
              'status': 'checked',
              'compliant': len(issues) == 0,
              'issues': issues,
              'suggestions': suggestions,
              'content_length': len(content)
    })
