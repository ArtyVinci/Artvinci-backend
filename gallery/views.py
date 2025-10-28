import os
import uuid
import base64
import json
import requests
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from .models import Artwork

load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")
IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}


def hf_post_model(model_id, payload, timeout=120):
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    r = requests.post(url, headers=HEADERS, json=payload, timeout=timeout)
    return r


def generate_image_bytes(prompt):
    r = hf_post_model(IMAGE_MODEL, {"inputs": prompt})
    if r.status_code != 200:
        print("Image API error:", r.status_code, r.text)
        return None

    ct = r.headers.get("content-type", "")
    # if direct image bytes
    if "image" in ct or "octet-stream" in ct:
        return r.content

    # otherwise try parse JSON -> base64
    try:
        j = r.json()
        if isinstance(j, dict) and j.get("image_base64"):
            return base64.b64decode(j["image_base64"])
    except Exception as e:
        print("Image parse error:", e)
    return None


def generate_art(request):
    if request.method == "POST":
        prompt = request.POST.get("prompt", "").strip()

        if not prompt:
            return render(request, "Gallery/generate.html", {"error_msg": "Please enter a prompt."})

        # Create DB entry (without image yet)
        art = Artwork(prompt=prompt)
        art.save()

        # Generate image
        image_bytes = generate_image_bytes(prompt)
        if image_bytes:
            filename = f"gallery/{uuid.uuid4().hex}.png"
            saved_name = default_storage.save(filename, ContentFile(image_bytes))
            # default_storage.url should give the uploaded URL (Cloudinary storage is configured in settings)
            url = default_storage.url(saved_name)
            art.image_url = url
            art.save()
            return redirect("generate_art")  # Avoid repost
        else:
            print("No image bytes returned for prompt:", prompt)
            return render(request, "Gallery/generate.html", {
                "error_msg": "Failed to generate image. Please try again.",
                "artworks": Artwork.objects.order_by("-created_at")
            })

    # GET
    artworks = Artwork.objects.order_by("-created_at")
    return render(request, "Gallery/generate.html", {"artworks": artworks})


# ---------------------------------------------------------------------------
# JSON API endpoints for frontend integration
# POST /api/gallery/generate/  -> { prompt }  returns generated artwork JSON
# GET  /api/gallery/           -> list of recent artworks
# ---------------------------------------------------------------------------


@csrf_exempt
@require_POST
def api_generate(request):
    """Accepts JSON { prompt } and returns JSON with generated artwork info."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return JsonResponse({'error': 'Prompt is required'}, status=400)

    # Create DB entry
    art = Artwork(prompt=prompt)
    art.save()

    # Generate image bytes (calls HF)
    image_bytes = generate_image_bytes(prompt)
    if image_bytes:
        filename = f"gallery/{uuid.uuid4().hex}.png"
        saved_name = default_storage.save(filename, ContentFile(image_bytes))
        url = default_storage.url(saved_name)
        art.image_url = url
        art.save()

        return JsonResponse({
            'id': str(art.id),
            'prompt': art.prompt,
            'image_url': art.image_url,
            'created_at': art.created_at.isoformat(),
        })

    return JsonResponse({'error': 'Image generation failed'}, status=500)


@require_GET
def api_list(request):
    artworks = Artwork.objects.order_by('-created_at')[:50]
    results = []
    for a in artworks:
        results.append({
            'id': str(a.id),
            'prompt': a.prompt,
            'image_url': a.image_url,
            'created_at': a.created_at.isoformat(),
        })
    return JsonResponse({'results': results})
