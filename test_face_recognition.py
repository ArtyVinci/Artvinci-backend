#!/usr/bin/env python3
"""
Face Recognition Testing Script
This script helps test the face recognition system with different images
to verify that it's actually comparing faces, not just checking registration status.
"""

import requests
import base64
import json
import sys
import os
from PIL import Image
import io

# Configuration
BACKEND_URL = "http://localhost:8000"  # Adjust if your backend runs on different port

def image_to_base64(image_path):
    """Convert image file to base64 string"""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{encoded_string}"
    except Exception as e:
        print(f"Error reading image {image_path}: {e}")
        return None

def test_face_login(image_path, description=""):
    """Test face login with a specific image"""
    print(f"\n{'='*60}")
    print(f"Testing face login with: {description}")
    print(f"Image: {image_path}")
    print(f"{'='*60}")

    # Convert image to base64
    image_data = image_to_base64(image_path)
    if not image_data:
        print("❌ Failed to load image")
        return

    # Make request to face login endpoint
    url = f"{BACKEND_URL}/api/auth/face/login/"
    payload = {"image": image_data}

    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'user' in data:
                print("✅ LOGIN SUCCESSFUL")
                print(f"User: {data['user']['email']}")
                if 'match_info' in data:
                    match_info = data['match_info']
                    print(f"Match Method: {match_info.get('method', 'unknown')}")
                    print(f"Cosine Similarity: {match_info.get('cosine', 'N/A')}")
                    print(f"Euclidean Distance: {match_info.get('distance', 'N/A')}")
                    print(f"Confidence: {match_info.get('confidence', 'N/A')}")
            else:
                print("❌ UNEXPECTED RESPONSE FORMAT")
                print(json.dumps(data, indent=2))
        else:
            data = response.json()
            print("❌ LOGIN FAILED")
            print(f"Error: {data.get('error', 'Unknown error')}")
            if 'debug_info' in data:
                debug = data['debug_info']
                print(f"Debug Info:")
                print(f"  - Best Distance: {debug.get('best_distance', 'N/A')}")
                print(f"  - Cosine Threshold: {debug.get('cos_threshold', 'N/A')}")
                print(f"  - Euclidean Threshold: {debug.get('euclid_threshold', 'N/A')}")
                print(f"  - Users Checked: {debug.get('users_checked', 'N/A')}")

    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON PARSE ERROR: {e}")
        print(f"Raw response: {response.text}")

def check_face_database():
    """Check what faces are registered in the database"""
    print(f"\n{'='*60}")
    print("CHECKING FACE DATABASE STATUS")
    print(f"{'='*60}")

    url = f"{BACKEND_URL}/api/auth/face/debug/"

    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ DATABASE STATUS RETRIEVED")
            print(f"Total Users: {data.get('total_users', 0)}")
            print(f"Users with Faces: {data.get('users_with_faces', 0)}")
            print(f"Users with Images: {data.get('users_with_images', 0)}")

            users_with_faces = data.get('users_with_face_encodings', [])
            if users_with_faces:
                print(f"\nRegistered Users with Face Encodings:")
                for user in users_with_faces:
                    print(f"  - {user['email']} (encoding length: {user['face_encoding_length']})")
            else:
                print("\nNo users with face encodings found!")
        else:
            print("❌ FAILED TO GET DATABASE STATUS")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {e}")

def main():
    print("Face Recognition Testing Script")
    print("This script tests if the face recognition system is actually comparing faces")
    print("and not just checking if faces are registered.\n")

    # Check database status first
    check_face_database()

    # Test with different images
    test_images = [
        ("path/to/your/face/image1.jpg", "Your face - should match"),
        ("path/to/different/person/image2.jpg", "Different person - should NOT match"),
        ("path/to/another/image3.jpg", "Another test image"),
    ]

    print(f"\n{'='*60}")
    print("FACE LOGIN TESTS")
    print(f"{'='*60}")
    print("Update the test_images list above with actual image paths to test.")
    print("Expected results:")
    print("- Your registered face should login successfully")
    print("- Different faces should fail to login")
    print("- Check the cosine similarity and distance values in the logs")

    # Uncomment and modify the paths below to test with actual images
    # for image_path, description in test_images:
    #     if os.path.exists(image_path):
    #     test_face_login(image_path, description)
    # else:
    #     print(f"Image not found: {image_path}")

    print(f"\n{'='*60}")
    print("HOW TO TEST:")
    print("1. Take photos of yourself and others")
    print("2. Update the test_images list with actual file paths")
    print("3. Run this script")
    print("4. Check the cosine similarity values:")
    print("   - Same person: should be > 0.5 (cosine similarity)")
    print("   - Different people: should be < 0.5")
    print("5. Also check the backend logs for detailed comparison results")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()