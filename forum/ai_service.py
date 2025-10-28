import os
import re
from typing import Optional

from django.conf import settings
import json

try:
    # Try to import langchain chat LLM wrappers (optional)
    # Prefer the community package import path when available (newer LangChain split)
    try:
        from langchain_core.prompts import PromptTemplate
    except Exception:
        # older langchain versions used a different path
        try:
            from langchain import PromptTemplate
        except Exception:
            PromptTemplate = None

    try:
        from langchain.chains import LLMChain
    except Exception:
        # LLMChain may be in langchain for older versions
        LLMChain = None

    # Try community chat model wrapper first (recommended)
    try:
        from langchain_community.chat_models import ChatGooglePalm as LangChainGoogleLLM
    except Exception:
        try:
            from langchain.chat_models import ChatGooglePalm as LangChainGoogleLLM
        except Exception:
            try:
                from langchain.llms import GooglePalm as LangChainGoogleLLM
            except Exception:
                LangChainGoogleLLM = None
except Exception:
    PromptTemplate = None
    LLMChain = None
    LangChainGoogleLLM = None

try:
    import google.generativeai as genai  # optional, used if available and configured
except Exception:
    genai = None


def _redact_pii(text: str) -> str:
    """Very small PII redaction to avoid sending emails / phones to external APIs.

    This is purposely conservative and simple for a prototype.
    """
    if not text:
        return text
    # redact emails
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email]", text)
    # redact simple phone numbers (sequences of 7+ digits)
    text = re.sub(r"\b\d{7,}\b", "[phone]", text)
    return text


def _clean_suggestion(text: str) -> str:
    """Clean and normalize suggestion text produced by LLMs or fallbacks.

    - Remove leading salutations/greetings (Bonjour, Salut, Hi, Merci pour le partage)
    - Remove verbose lead-ins like "Je comprends que ..." so the reply starts
      directly with helpful content.
    - Trim and ensure capitalization.
    """
    if not text:
        return text
    t = text.strip()
    # remove common French and English salutations at start
    t = re.sub(r'^(bonjour|salut|hi|hello|merci pour le partage)[\s,;:!-]+', '', t, flags=re.I)
    # remove common french lead-ins like "Je comprends que" or "Je comprends"
    t = re.sub(r'^(je comprends(?: que)?)[\s,:;-]+', '', t, flags=re.I)
    # sometimes models prefix with "Voici une piste de réponse :" — remove it
    t = re.sub(r'^voici (une )?(piste|proposition) de r(?:é|e)ponse\s*[:\-–]?\s*', '', t, flags=re.I)
    t = t.strip()
    if not t:
        return t
    # ensure first character is uppercase
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t


def suggest_reply(topic=None, last_replies=None, tone: str = "friendly", max_length: int = 200, user=None, use_langchain_only: bool = False):
    """Return a suggested reply string for a topic.

    - topic: object with `title` and `content` attributes (e.g., ForumTopic) or dict.
    - last_replies: iterable of reply objects/dicts with 'content' fields (most recent first)
    - tone: 'friendly'|'formal'|'concise'
    - max_length: max characters in suggestion

    This function uses the `google-generativeai` client if available and a GEMINI_API_KEY
    is configured in settings or environment. Otherwise it falls back to a lightweight
    template-based suggestion so the endpoint remains usable offline for testing.
    """
    title = None
    content = None
    try:
        if isinstance(topic, dict):
            title = topic.get('title')
            content = topic.get('content')
        else:
            title = getattr(topic, 'title', None)
            content = getattr(topic, 'content', None)
    except Exception:
        title = None
        content = None

    # Build context
    context_parts = []
    if title:
        context_parts.append(f"Topic: {title}")
    if content:
        context_parts.append(content)
    if last_replies:
        for r in (last_replies or [])[:5]:
            c = r.get('content') if isinstance(r, dict) else getattr(r, 'content', None)
            if c:
                context_parts.append(f"Reply: {c}")

    context = "\n---\n".join([_redact_pii(p) for p in context_parts if p])

    # If LangChain is available, build a richer prompt template to produce
    # a personalized reply and request structured JSON output.
    if PromptTemplate and LLMChain and LangChainGoogleLLM is not None:
        try:
            template = (
                "You are an assistant specialized in writing personalized forum replies for an art community.\n"
                "Given the context, produce a concise, helpful, and specific reply that references the topic details.\n"
                "Read the ENTIRE post content below and explicitly reference at least one specific phrase or sentence from it (quote it briefly) to show you read it.\n"
                "Do NOT start the reply with a greeting or salutation (e.g., 'Bonjour', 'Salut', 'Merci pour le partage').\n"
                "Focus on concrete, actionable suggestions (1-3 short steps) tailored to the author's problem, and finish with a targeted follow-up question that invites a specific next action.\n"
                "If the author mentions a material, technique, or constraint, incorporate that into the suggestion.\n"
                "Avoid repetition and avoid exposing personal data.\n\n"
                "Context:\nTitle: {title}\nFull post: {post}\nLast replies: {last_replies}\nAuthor: {author}\n\n"
                "Tone: {tone}\nLength limit: {max_length} characters\n\n"
                "Output as JSON with keys: suggestion (string) and rationale (string).\n"
                "Ensure the `suggestion` field contains the reply text only (no salutations) and is no longer than {max_length} characters."
            )

            prompt = PromptTemplate.from_template(template)
            # prepare api key and try multiple instantiation strategies for LangChain wrappers
            api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
            llm = None
            last_exc = None
            if api_key:
                # Try instantiating with explicit model name (gemini-2.5-flash) which
                # is recommended for better responses. Try several constructor patterns
                # to handle different LangChain wrapper versions.
                tried = []
                try:
                    llm = LangChainGoogleLLM(model="gemini-2.5-flash", api_key=api_key, temperature=0.2)
                    tried.append('model+api_key')
                except Exception as e:
                    last_exc = e
                if llm is None:
                    try:
                        llm = LangChainGoogleLLM(model="gemini-2.5-flash", google_api_key=api_key, temperature=0.2)
                        tried.append('model+google_api_key')
                    except Exception as e:
                        last_exc = e
                # try without explicit model but set env vars the wrapper may read
                if llm is None:
                    try:
                        os.environ.setdefault('GOOGLE_API_KEY', api_key)
                        os.environ.setdefault('GEMINI_API_KEY', api_key)
                        llm = LangChainGoogleLLM(model="gemini-2.5-flash")
                        tried.append('env+model')
                    except Exception as e:
                        last_exc = e
                # final fallback: instantiate without model, let wrapper default (less ideal)
                if llm is None:
                    try:
                        llm = LangChainGoogleLLM(api_key=api_key)
                        tried.append('api_key_only')
                    except Exception as e:
                        last_exc = e
            else:
                last_exc = RuntimeError('GEMINI_API_KEY not configured')

            if llm is None:
                # raise the last exception to be caught by outer try
                raise last_exc

            chain = LLMChain(llm=llm, prompt=prompt)

            author_name = getattr(user, 'username', None) if user is not None else 'Auteur'
            last_replies_text = '\n'.join([_redact_pii(r.get('content') if isinstance(r, dict) else getattr(r, 'content', '')) for r in (last_replies or [])])

            # Provide the full post content in the prompt (unredacted except PII)
            post_text = content or ''

            inputs = {
                'title': title or '',
                'content': content or '',
                'post': post_text,
                'last_replies': last_replies_text,
                'author': author_name,
                'tone': tone,
                'max_length': max_length,
            }

            resp_text = chain.run(inputs)
            # Attempt to parse JSON from the LLM response
            try:
                parsed = json.loads(resp_text)
                suggestion = parsed.get('suggestion') or parsed.get('reply') or ''
                rationale = parsed.get('rationale') or ''
            except Exception:
                # Fallback: use full response as suggestion
                suggestion = resp_text.strip()
                rationale = ''

            # Clean greetings and generic lead-ins to start directly with helpful text
            suggestion = _clean_suggestion(suggestion)

            if suggestion and len(suggestion) > max_length:
                suggestion = suggestion[: max_length - 3].rstrip() + '...'
            return {'suggestion': suggestion, 'model': 'langchain-gemini', 'cached': False, 'rationale': rationale}
        except Exception as e:
            # If anything fails in the LangChain path, return error indicator when
            # caller specifically requested LangChain-only behavior. Include detail
            # to aid debugging.
            if use_langchain_only:
                msg = str(e)
                # common incompatibility: google.generativeai types changed and
                # LangChain wrappers may expect MessageDict. Provide a helpful
                # actionable suggestion in that case.
                if 'MessageDict' in msg or "has no attribute 'MessageDict'" in msg:
                    msg = (
                        msg
                        + " — This usually means your installed google-generativeai or langchain-community"
                        + " package is incompatible. Try upgrading them in the venv:\n"
                        + "pip install -U google-generativeai langchain-community"
                    )
                return {'error': 'langchain_failed', 'detail': msg}
            # otherwise fall back to other approaches
            pass
    # If caller explicitly requested LangChain-only and we reached here,
    # signal that LangChain is unavailable.
    if use_langchain_only:
        return {'error': 'langchain_unavailable'}

    # Otherwise fall back to simple prompt
    prompt = (
        "You are a helpful assistant that writes short friendly forum replies. "
        f"Tone: {tone}. Keep the reply constructive and respectful.\n\n"
        f"Context:\n{context}\n\nWrite a short reply (<= {max_length} characters)."
    )

    # Try to call external API if available and configured
    api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
    if genai and api_key:
        try:
            # configure client safely
            try:
                genai.configure(api_key=api_key)
            except Exception:
                # some versions may use configuration via environment; ignore if fails
                pass
            # Use a simple text generation call if available; guard for API differences
            if hasattr(genai, 'generate_text'):
                resp = genai.generate_text(prompt=prompt, max_output_tokens=400)
                # the response shape may vary; attempt to extract text
                text = getattr(resp, 'text', None) or resp.get('candidates', [{}])[0].get('content') if isinstance(resp, dict) else None
            else:
                # fallback for older/newer clients: try a generic call
                resp = genai._client.generate(prompt)
                text = getattr(resp, 'text', None) or (resp.candidates[0].content if getattr(resp, 'candidates', None) else None)
            if not text:
                raise RuntimeError('No text returned from generative client')
            suggestion = text.strip()
            if len(suggestion) > max_length:
                suggestion = suggestion[: max_length - 3].rstrip() + '...'
            return {
                'suggestion': suggestion,
                'model': getattr(resp, 'model', 'gemini') if isinstance(resp, dict) else getattr(resp, 'model', None),
                'cached': False,
            }
        except Exception:
            # any error -> fallback to template
            pass

    # Local fallback: simple template-based reply
    # Local fallback: produce a more actionable, non-greeting reply using heuristics
    # Summarize the user's issue (short) and provide 2-3 concrete suggestions.
    summary = ''
    if content:
        # use first meaningful clause as a short summary
        first_line = content.strip().split('\n')[0]
        # remove common salutations from user content
        first_line = re.sub(r'^(bonjour|salut|hello|hi)[\s,;:-]+', '', first_line, flags=re.I)
        # truncate to reasonable length
        if len(first_line) > 120:
            first_line = first_line[:117].rsplit(' ', 1)[0] + '...'
        summary = first_line

    advice_parts = []
    if summary:
        advice_parts.append(f"Vous mentionnez: «{summary}».")
        advice_parts.append("Essayez d'abord d'ajuster la dilution de la peinture et d'utiliser un medium pour améliorer la fluidité.")
        advice_parts.append("Testez la technique sur un petit échantillon et partagez une photo pour obtenir des retours précis.")
    else:
        advice_parts.append("Pouvez-vous préciser le problème (matériel, technique, ou rendu) ?")

    body = ' '.join(advice_parts)
    suggestion = f"Voici une proposition de réponse concise :\n\n{body}\n\nAvez-vous déjà essayé ces pistes ?"
    suggestion = _clean_suggestion(suggestion)
    if len(suggestion) > max_length:
        suggestion = suggestion[: max_length - 3].rstrip() + '...'

    return {'suggestion': suggestion, 'model': 'fallback', 'cached': False}
