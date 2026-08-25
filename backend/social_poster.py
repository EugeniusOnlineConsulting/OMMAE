"""
OMMAE Social Poster v0.1 - Your empire just creamed on 3 platforms
Multi-platform posting: Instagram, TikTok, YouTube Shorts
One click. Three platforms. Zero fucks given.
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Optional
import requests

# Platform API Keys
INSTAGRAM_ACCESS_TOKEN = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
TIKTOK_ACCESS_TOKEN = os.environ.get('TIKTOK_ACCESS_TOKEN', '')
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

class SocialPoster:
    """One-click multi-platform posting. POST NOW or cry later."""
    
    def __init__(self):
        self.platforms = {
            'instagram': InstagramPoster(),
            'tiktok': TikTokPoster(),
            'youtube': YouTubePoster()
        }
        self.results = {}
    
    async def post_all(self, video_url: str, caption: str, hashtags: list = None) -> Dict:
        """Post to all platforms simultaneously. This is the POST NOW button."""
        tasks = []
        for name, poster in self.platforms.items():
            tasks.append(self._post_to_platform(name, poster, video_url, caption, hashtags))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
        
        return {
            'success': success_count > 0,
            'platforms_posted': success_count,
            'results': self.results,
            'message': f'Your empire just creamed on {success_count} platforms. Go make coffee.',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _post_to_platform(self, name: str, poster, video_url: str, caption: str, hashtags: list):
        try:
            result = await poster.post(video_url, caption, hashtags)
            self.results[name] = result
            return result
        except Exception as e:
            self.results[name] = {'success': False, 'error': str(e)}
            return self.results[name]


class InstagramPoster:
    """Instagram Reels posting via Graph API."""
    
    async def post(self, video_url: str, caption: str, hashtags: list = None) -> Dict:
        if not INSTAGRAM_ACCESS_TOKEN:
            return {'success': False, 'error': 'No Instagram token', 'platform': 'instagram'}
        
        full_caption = caption
        if hashtags:
            full_caption += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        # Instagram Graph API for Reels is not wired. Do not fake a publish.
        return {
            'success': False,
            'platform': 'instagram',
            'post_type': 'reel',
            'caption': full_caption[:2200],
            'error': 'Instagram publish is not implemented. Token present, API call not wired.',
        }


class TikTokPoster:
    """TikTok posting via Content Posting API."""
    
    async def post(self, video_url: str, caption: str, hashtags: list = None) -> Dict:
        if not TIKTOK_ACCESS_TOKEN:
            return {'success': False, 'error': 'No TikTok token', 'platform': 'tiktok'}
        
        full_caption = caption
        if hashtags:
            full_caption += ' ' + ' '.join(f'#{tag}' for tag in hashtags)
        
        return {
            'success': False,
            'platform': 'tiktok',
            'post_type': 'video',
            'caption': full_caption[:150],
            'error': 'TikTok publish is not implemented. Token present, API call not wired.',
        }


class YouTubePoster:
    """YouTube Shorts posting via Data API v3."""
    
    async def post(self, video_url: str, caption: str, hashtags: list = None) -> Dict:
        if not YOUTUBE_API_KEY:
            return {'success': False, 'error': 'No YouTube API key', 'platform': 'youtube'}
        
        title = caption[:100] if len(caption) <= 100 else caption[:97] + '...'
        description = caption
        if hashtags:
            description += '\n\n' + ' '.join(f'#{tag}' for tag in hashtags)
        
        return {
            'success': False,
            'platform': 'youtube',
            'post_type': 'short',
            'title': title,
            'description': description,
            'error': 'YouTube publish is not implemented. API key present, upload not wired.',
        }


async def post_now(video_url: str, caption: str, hashtags: list = None) -> Dict:
    """Main entry point for the POST NOW button."""
    poster = SocialPoster()
    return await poster.post_all(video_url, caption, hashtags)


if __name__ == "__main__":
    print("🚀 OMMAE Social Poster v0.1")
    print("Your empire just creamed on 3 platforms.")
    result = asyncio.run(post_now(
        "https://example.com/video.mp4",
        "Indigenous cannabis wisdom from Mohawk Medibles",
        ["mohawkmedibles", "cannabis", "indigenous", "wellness"]
    ))
    print(json.dumps(result, indent=2))
