#!/usr/bin/env python
import sys
print('Python executable:', sys.executable)
try:
    import langchain
    print('langchain version:', getattr(langchain, '__version__', 'unknown'))
except Exception as e:
    print('langchain import failed:', e)
try:
    from langchain.chat_models import ChatGooglePalm
    print('ChatGooglePalm: available')
except Exception as e:
    print('ChatGooglePalm import failed:', e)
try:
    from langchain.llms import GooglePalm
    print('GooglePalm: available')
except Exception as e:
    print('GooglePalm import failed:', e)
try:
    import google.generativeai as genai
    print('google.generativeai import ok')
except Exception as e:
    print('google.generativeai import failed:', e)

print('\nCheck complete')
