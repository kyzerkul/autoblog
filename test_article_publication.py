#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de test pour la publication d'articles complets sur WordPress
"""
import os
import requests
from dotenv import load_dotenv
import json
import re
import time

# Charger les variables d'environnement
load_dotenv(override=True)

# Récupérer les informations de connexion
wordpress_url = os.getenv("WORDPRESS_URL", "").rstrip('/')
username = os.getenv("WORDPRESS_USERNAME", "")
app_password = os.getenv("WORDPRESS_APP_PASSWORD", "")
api_url = f"{wordpress_url}/wp-json/wp/v2"
auth = (username, app_password)

print(f"=== Test de publication d'article complet ===")
print(f"WordPress URL: {wordpress_url}")
print(f"WordPress API URL: {api_url}")

def sanitize_content(content):
    """Nettoie le contenu HTML pour éviter les problèmes avec WordPress"""
    if not content:
        return ""
    
    # Supprimer les scripts
    content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
    # Supprimer les styles
    content = re.sub(r'<style.*?</style>', '', content, flags=re.DOTALL)
    # Supprimer les iframes
    content = re.sub(r'<iframe.*?</iframe>', '', content, flags=re.DOTALL)
    # Limiter la longueur si nécessaire (WordPress peut avoir des limites)
    if len(content) > 50000:
        content = content[:50000] + "..."
    
    return content

def test_publish_article(title, content, meta_description="", include_youtube=False):
    """Test la publication d'un article avec différents niveaux de complexité"""
    
    # Étape 1: Nettoyer le contenu
    content = sanitize_content(content)
    
    # Étape 2: Ajouter une vidéo YouTube si demandé
    if include_youtube:
        video_id = "dQw4w9WgXcQ"  # ID de test
        video_embed = f'''
        <p><a href="https://www.youtube.com/watch?v={video_id}" target="_blank">Voir la vidéo sur YouTube</a></p>
        '''
        content = content + video_embed
    
    # Étape 3: Créer les données de l'article
    post_data = {
        "title": title,
        "content": content,
        "status": "draft"
    }
    
    # Ajouter la méta description si fournie
    if meta_description:
        post_data["excerpt"] = meta_description
    
    # Étape 4: Envoyer la requête
    print(f"\nPublication de l'article: {title}")
    print(f"Longueur du contenu: {len(content)} caractères")
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        response = requests.post(
            f"{api_url}/posts",
            json=post_data,
            auth=auth,
            headers=headers,
            timeout=30
        )
        
        print(f"Code de statut: {response.status_code}")
        
        if response.status_code == 201:
            post_id = response.json().get("id")
            print(f"✅ Succès! Article publié avec ID: {post_id}")
            
            # Étape 5 (optionnelle): Ajouter une image mise en avant
            if include_youtube and post_id:
                try:
                    # Simuler l'ajout d'une image mise en avant
                    print("Mise à jour de l'image mise en avant...")
                    time.sleep(1)  # Pause pour simuler le téléchargement
                    print("✅ Image mise en avant ajoutée (simulée)")
                except Exception as img_error:
                    print(f"❌ Erreur lors de l'ajout de l'image: {str(img_error)}")
            
            return True, post_id
        else:
            print(f"❌ Échec de la publication. Code {response.status_code}")
            try:
                error_json = response.json()
                if 'message' in error_json:
                    print(f"Message d'erreur: {error_json['message']}")
                print(f"Détails de la réponse: {json.dumps(error_json, indent=2)[:500]}...")
            except:
                print(f"Réponse brute: {response.text[:500]}...")
            return False, None
    
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

def run_tests():
    """Exécute une série de tests pour identifier le problème"""
    
    # Test 1: Article minimal (devrait toujours fonctionner)
    print("\n=== Test 1: Article minimal ===")
    success, post_id = test_publish_article(
        "Test 1 - Article Minimal",
        "<p>Ceci est un contenu de test minimal.</p>"
    )
    
    # Test 2: Article avec méta description
    print("\n=== Test 2: Article avec méta description ===")
    success, post_id = test_publish_article(
        "Test 2 - Article avec Méta Description",
        "<p>Ceci est un article avec une méta description.</p>",
        "Ceci est une méta description de test pour voir si elle cause un problème."
    )
    
    # Test 3: Article avec lien YouTube
    print("\n=== Test 3: Article avec lien YouTube ===")
    success, post_id = test_publish_article(
        "Test 3 - Article avec Lien YouTube",
        "<p>Ceci est un article avec un lien YouTube à la fin.</p>",
        "",
        True
    )
    
    # Test 4: Article plus long
    print("\n=== Test 4: Article plus long ===")
    long_content = "<h2>Titre de section</h2>" + "<p>Paragraphe de test.</p>" * 50
    success, post_id = test_publish_article(
        "Test 4 - Article Plus Long",
        long_content
    )
    
    # Test 5: Article complet
    print("\n=== Test 5: Article complet ===")
    complete_content = """
    <h1>Titre principal</h1>
    <p>Introduction à l'article.</p>
    <h2>Première section</h2>
    <p>Contenu de la première section avec <strong>du texte en gras</strong> et <em>en italique</em>.</p>
    <ul>
        <li>Point 1</li>
        <li>Point 2</li>
        <li>Point 3</li>
    </ul>
    <h2>Deuxième section</h2>
    <p>Contenu de la deuxième section avec un <a href="https://example.com">lien exemple</a>.</p>
    <blockquote>Ceci est une citation.</blockquote>
    <h3>Sous-section</h3>
    <p>Contenu de la sous-section.</p>
    """
    success, post_id = test_publish_article(
        "Test 5 - Article Complet",
        complete_content,
        "Description complète de l'article de test avec tous les éléments.",
        True
    )

if __name__ == "__main__":
    run_tests()
    print("\n=== Tests terminés ===")
