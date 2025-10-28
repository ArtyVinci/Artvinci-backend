#!/usr/bin/env python
import os, sys
BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, BASE)
from forum import ai_service
print('PromptTemplate is', ai_service.PromptTemplate)
print('LLMChain is', ai_service.LLMChain)
print('LangChainGoogleLLM is', ai_service.LangChainGoogleLLM)
