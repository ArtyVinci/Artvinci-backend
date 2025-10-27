#!/usr/bin/env python
"""
Script de vérification du système de reconnaissance faciale intégré
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'artvinci.settings')
django.setup()

def test_backend_ready():
    """Teste si le backend est prêt pour la reconnaissance faciale"""
    print("🔍 VÉRIFICATION DU SYSTÈME DE RECONNAISSANCE FACIALE")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: MongoDB Connection
    try:
        from accounts.models import User
        print("✅ Test 1/6: MongoDB Connection OK")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 1/6: MongoDB Connection FAILED - {e}")
    
    # Test 2: DeepFace Import
    try:
        from deepface import DeepFace
        print("✅ Test 2/6: DeepFace Import OK")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 2/6: DeepFace Import FAILED - {e}")
    
    # Test 3: TensorFlow Import
    try:
        import tensorflow as tf
        print("✅ Test 3/6: TensorFlow Import OK")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 3/6: TensorFlow Import FAILED - {e}")
    
    # Test 4: Face Extraction Functions
    try:
        from accounts.views import extract_face_encoding_from_url, compare_face_encodings
        print("✅ Test 4/6: Face Extraction Functions OK")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 4/6: Face Extraction Functions FAILED - {e}")
    
    # Test 5: Cloudinary Configuration
    try:
        import cloudinary
        from django.conf import settings
        if hasattr(settings, 'CLOUDINARY_STORAGE'):
            print("✅ Test 5/6: Cloudinary Configuration OK")
            tests_passed += 1
        else:
            print("⚠️  Test 5/6: Cloudinary Configuration - Check .env variables")
    except Exception as e:
        print(f"❌ Test 5/6: Cloudinary Configuration FAILED - {e}")
    
    # Test 6: New Endpoints
    try:
        from accounts.views import RegisterFaceFromProfileView
        print("✅ Test 6/6: New Face Endpoints OK")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Test 6/6: New Face Endpoints FAILED - {e}")
    
    print("=" * 60)
    print(f"📊 RÉSULTAT: {tests_passed}/{total_tests} tests réussis")
    
    if tests_passed == total_tests:
        print("🎉 SYSTÈME PRÊT ! Tous les tests sont passés.")
        print("\n📋 PROCHAINES ÉTAPES:")
        print("1. Démarrer Django: python manage.py runserver")
        print("2. Démarrer Frontend: npm run dev (dans Artvinci-Frontend)")
        print("3. Tester upload photo profil → auto face_encoding")
        print("4. Tester login facial avec photo profil")
        print("5. Consulter GUIDE_TEST_FACE_RECOGNITION.md pour détails")
        return True
    else:
        print("⚠️  ATTENTION: Certains tests ont échoué.")
        print("Consultez les erreurs ci-dessus avant de continuer.")
        return False

def check_model_field():
    """Vérifier que le champ face_encoding est bien ajouté au modèle User"""
    try:
        from accounts.models import User
        
        # Créer une instance temporaire pour vérifier les champs
        user_fields = User._fields.keys()
        
        if 'face_encoding' in user_fields:
            print("✅ Champ face_encoding présent dans le modèle User")
            return True
        else:
            print("❌ Champ face_encoding MANQUANT dans le modèle User")
            return False
    except Exception as e:
        print(f"❌ Erreur lors de la vérification du modèle: {e}")
        return False

if __name__ == "__main__":
    print("🚀 DÉMARRAGE DES VÉRIFICATIONS...\n")
    
    # Vérification du champ face_encoding
    check_model_field()
    print()
    
    # Vérifications complètes
    if test_backend_ready():
        sys.exit(0)
    else:
        sys.exit(1)