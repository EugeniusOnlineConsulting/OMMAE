"""
OMMAE Video Pipeline v0.1 - The heartbeat of content generation
"""
import os, json, asyncio
from datetime import datetime
import anthropic
import google.generativeai as genai
import requests

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
KLING_API_KEY = os.environ.get('KLING_API_KEY', '')

claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class VideoPipeline:
    def __init__(self, brand="mohawk_medibles"):
        self.brand = brand
        self.stages = ['research', 'script', 'video', 'process', 'stage']
        
    async def run(self, topic=None):
        research = await self.research_topic(topic)
        script = await self.generate_script(research)
        video = await self.generate_video(script)
        processed = await self.process_video(video)
        return await self.stage_video(processed, script)
    
    async def research_topic(self, topic=None):
        if not topic:
            import random
            topic = random.choice(["Indigenous wellness", "Cannabis education", "Behind the scenes"])
        prompt = f"Research for Mohawk Medibles: {topic}. Provide key points, compliance notes, social hook."
        if claude_client:
            r = claude_client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1024, messages=[{"role":"user","content":prompt}])
            return {"topic": topic, "research": r.content[0].text}
        model = genai.GenerativeModel('gemini-pro')
        return {"topic": topic, "research": model.generate_content(prompt).text}
    
    async def generate_script(self, research):
        prompt = f"Create 15-30s video script for Mohawk Medibles. Research: {json.dumps(research)}"
        if claude_client:
            r = claude_client.messages.create(model="claude-sonnet-4-20250514", max_tokens=1024, messages=[{"role":"user","content":prompt}])
            return {"script": r.content[0].text}
        model = genai.GenerativeModel('gemini-pro')
        return {"script": model.generate_content(prompt).text}
    
    async def generate_video(self, script):
        return "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
    
    async def process_video(self, url):
        return url
    
    async def stage_video(self, url, script):
        return {"video_url": url, "status": "staged", "ready_to_post": True}

async def generate_content(topic=None):
    return await VideoPipeline().run(topic)
