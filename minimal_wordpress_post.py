#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script minimaliste pour tester la publication sur WordPress
"""
import os
import requests
from dotenv import load_dotenv
import json

# Charger les variables d'environnement
load_dotenv(override=True)

# Récupérer les informations de connexion
wordpress_url = os.getenv("WORDPRESS_URL", "").rstrip('/')
username = os.getenv("WORDPRESS_USERNAME", "")
app_password = os.getenv("WORDPRESS_APP_PASSWORD", "")
api_url = f"{wordpress_url}/wp-json/wp/v2"
auth = (username, app_password)

# Fonction pour publier un article minimal
def publish_minimal_post():
    print(f"WordPress URL: {wordpress_url}")
    print(f"WordPress API URL: {api_url}")
    print(f"Username: {username}")
    print(f"Password length: {len(app_password) if app_password else 0}")
    
    # Créer un article avec le contenu minimum
    minimal_post = {
        "title": "Test Article Minimal",
        "content": "<p>Ceci est un test simple.</p>",
        "status": "draft"
    }
    
    try:
        # Définir les en-têtes
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Faire la requête
        print("Envoi de la requête minimale...")
        response = requests.post(
            f"{api_url}/posts",
            json=minimal_post,
            auth=auth,
            headers=headers,
            timeout=30
        )
        
        # Afficher les résultats
        print(f"Code de statut: {response.status_code}")
        print(f"Réponse: {response.text[:500]}...")
        
        if response.status_code == 201:
            print("✅ Succès! Article minimal créé.")
            post_id = response.json().get("id")
            print(f"ID de l'article: {post_id}")
            return True
        else:
            print("❌ Échec de la création de l'article minimal.")
            # Analyser l'erreur
            try:
                error_json = response.json()
                if 'message' in error_json:
                    print(f"Message d'erreur: {error_json['message']}")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# Exécuter le test
if __name__ == "__main__":
    print("=== Test minimaliste de publication WordPress ===\n")
    result = publish_minimal_post()
    
    if result:
        print("\n✅ Test réussi! La publication WordPress fonctionne.")
    else:
        print("\n❌ Test échoué! La publication WordPress ne fonctionne pas.")
