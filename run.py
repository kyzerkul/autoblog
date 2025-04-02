#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de démarrage pour l'application Flask
Ce script configure l'environnement d'encodage avant de lancer l'application
"""

import os
import sys
import codecs
import locale

# Force l'encodage UTF-8 pour sys.stdout et sys.stderr
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Configuration de l'encodage
os.environ["LANG"] = "en_US.UTF-8"
os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Tentative de configuration du locale
try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, '')  # Locale par défaut du système
    except locale.Error:
        pass

# Méthode alternative pour gérer l'encodage des sorties
def patch_io_encoding():
    if sys.stdout.encoding != 'utf-8':
        if hasattr(sys.stdout, 'detach'):
            try:
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            except:
                pass
    if sys.stderr.encoding != 'utf-8':
        if hasattr(sys.stderr, 'detach'):
            try:
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
            except:
                pass

patch_io_encoding()

# Remplacer les détecteurs de codecs pour forcer UTF-8
def utf8_encoder(encoding):
    return codecs.getencoder('utf-8')

codecs.register(lambda name: utf8_encoder('ascii') if name == 'ascii' else None)

# Importer et exécuter l'application Flask
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
