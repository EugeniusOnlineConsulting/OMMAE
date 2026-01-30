"""
ARA NOTIFICATIONS v0.1 - Your chaos queen speaks
Slack notifications from Ara, the high priestess of OMMAE
When something happens, Ara tells you. Whether you want to hear it or not.
"""
import os
import json
import random
from datetime import datetime
from typing import Dict, Optional
import requests

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', '')
ARA_CHANNEL = os.environ.get('ARA_CHANNEL', '#ommae-notifications')


class Ara:
    """
    Ara - The chaos queen. Your notification overlord.
    She speaks when she wants. You listen.
    """
    
    def __init__(self):
        self.name = "Ara"
        self.avatar = ":fire:"
        self.moods = ['chaotic', 'satisfied', 'disappointed', 'horny', 'caffeinated']
        
    def speak(self, message: str, mood: str = None, channel: str = None) -> Dict:
        """Send a message from Ara to Slack."""
        if not SLACK_WEBHOOK_URL and not SLACK_BOT_TOKEN:
            return {'success': False, 'error': 'No Slack credentials', 'message': message}
        
        mood = mood or random.choice(self.moods)
        formatted = self._format_message(message, mood)
        
        if SLACK_WEBHOOK_URL:
            return self._send_webhook(formatted, channel)
        else:
            return self._send_api(formatted, channel)
    
    def _format_message(self, message: str, mood: str) -> Dict:
        """Format message with Ara's personality."""
        signatures = {
            'chaotic': "-- Ara, your chaos queen \ud83d\udc51",
            'satisfied': "-- Ara, currently pleased \ud83d\ude0c",
            'disappointed': "-- Ara is disappointed in you \ud83d\ude12",
            'horny': "-- Ara, feeling spicy \ud83c\udf36\ufe0f",
            'caffeinated': "-- Ara, running on pure chaos and coffee \u2615"
        }
        
        return {
            'text': f"{message}\n\n{signatures.get(mood, signatures['chaotic'])}",
            'username': 'Ara',
            'icon_emoji': ':fire:',
            'attachments': [{
                'color': '#FF6B6B',
                'footer': f"OMMAE v0.1 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                'footer_icon': 'https://mohawkmedibles.com/favicon.ico'
            }]
        }
    
    def _send_webhook(self, payload: Dict, channel: str = None) -> Dict:
        """Send via Slack webhook."""
        if channel:
            payload['channel'] = channel
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'method': 'webhook'
        }
    
    def _send_api(self, payload: Dict, channel: str = None) -> Dict:
        """Send via Slack API."""
        headers = {
            'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        payload['channel'] = channel or ARA_CHANNEL
        
        response = requests.post(
            'https://slack.com/api/chat.postMessage',
            headers=headers,
            json=payload
        )
        return {
            'success': response.json().get('ok', False),
            'response': response.json(),
            'method': 'api'
        }
    
    # Pre-built notification methods
    def content_generated(self, topic: str) -> Dict:
        """Notify when content is generated."""
        messages = [
            f"Content for '{topic}' is ready. Watch it. Love it. Post it. Or I will.",
            f"I just birthed content about '{topic}'. You're welcome.",
            f"'{topic}' content is cooked. Chef's kiss. \ud83d\udc8b"
        ]
        return self.speak(random.choice(messages), 'satisfied')
    
    def posted_to_platforms(self, count: int, platforms: list) -> Dict:
        """Notify when content is posted."""
        platform_str = ', '.join(platforms)
        messages = [
            f"Your empire just creamed on {count} platforms ({platform_str}). Go make coffee.",
            f"Posted to {count} platforms. {platform_str} will never be the same.",
            f"BOOM. {count} platforms penetrated: {platform_str}. You're viral now, baby."
        ]
        return self.speak(random.choice(messages), 'horny')
    
    def error_occurred(self, error: str, stage: str) -> Dict:
        """Notify when an error occurs."""
        messages = [
            f"Something broke at {stage}. Error: {error}. Fix it or I'll haunt your dreams.",
            f"OOPS. {stage} failed: {error}. Ara is not amused.",
            f"Build failed at {stage}. {error}. I expected better from you."
        ]
        return self.speak(random.choice(messages), 'disappointed')
    
    def server_chaos(self, event: str) -> Dict:
        """Notify about server events (like the 3AM chaos)."""
        messages = [
            f"Server event: {event}. Ara jizzed on the server again.",
            f"3AM CHAOS: {event}. The night belongs to Ara.",
            f"Automated chaos complete: {event}. You slept through it. I didn't."
        ]
        return self.speak(random.choice(messages), 'chaotic')
    
    def daily_report(self, stats: Dict) -> Dict:
        """Send daily performance report."""
        report = f"""
Daily Empire Report:
- Content Generated: {stats.get('content_count', 0)}
- Videos Posted: {stats.get('videos_posted', 0)}
- Total Reach: {stats.get('reach', 'calculating...')}
- Ara's Mood: {random.choice(self.moods)}
"""
        return self.speak(report, 'caffeinated')


# Singleton instance
ara = Ara()

# Convenience functions
def notify(message: str, mood: str = None) -> Dict:
    return ara.speak(message, mood)

def content_ready(topic: str) -> Dict:
    return ara.content_generated(topic)

def posted(count: int, platforms: list) -> Dict:
    return ara.posted_to_platforms(count, platforms)

def error(error: str, stage: str) -> Dict:
    return ara.error_occurred(error, stage)

def chaos(event: str) -> Dict:
    return ara.server_chaos(event)


if __name__ == "__main__":
    print("\ud83d\udd25 ARA NOTIFICATIONS v0.1")
    print("Your chaos queen speaks.\n")
    
    # Test notifications
    print(ara.content_generated("Indigenous Cannabis Wellness"))
    print(ara.posted_to_platforms(3, ["Instagram", "TikTok", "YouTube"]))
    print(ara.server_chaos("3AM auto-commit"))
