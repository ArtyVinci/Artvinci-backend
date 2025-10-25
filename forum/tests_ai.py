from django.test import SimpleTestCase

from .ai_service import suggest_reply


class AISuggestReplyTests(SimpleTestCase):

    def test_suggest_reply_fallback_basic(self):
        topic = {'title': 'Help with painting technique', 'content': 'I am struggling with blending acrylics on canvas.'}
        result = suggest_reply(topic=topic, last_replies=[{'content': 'Have you tried thinning your paint?'}], tone='friendly', max_length=500)
        self.assertIsInstance(result, dict)
        self.assertIn('suggestion', result)
        self.assertTrue(len(result['suggestion']) > 0)

    def test_suggest_reply_short_max_length(self):
        topic = {'title': 'Short question', 'content': 'How to frame a canvas?'}
        result = suggest_reply(topic=topic, last_replies=[], tone='concise', max_length=40)
        self.assertIsInstance(result, dict)
        self.assertIn('suggestion', result)
        self.assertLessEqual(len(result['suggestion']), 40)
