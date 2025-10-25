#!/usr/bin/env python
import os
import django
import sys

# ensure project package is importable
BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'artvinci.settings')
try:
    django.setup()
except Exception as e:
    print('Django setup failed:', e)
    raise

from forum.ai_service import suggest_reply

class DummyTopic:
    def __init__(self, title, content):
        self.title = title
        self.content = content


def main():
    topic = DummyTopic('Test topic', 'This is a test content about art and painting techniques.')
    print('GEMINI_API_KEY:', os.environ.get('GEMINI_API_KEY'))
    print('Running suggest_reply(use_langchain_only=True)')
    res = suggest_reply(topic=topic, last_replies=[], tone='friendly', max_length=300, user=None, use_langchain_only=True)
    print('Result:', res)

if __name__ == '__main__':
    main()
