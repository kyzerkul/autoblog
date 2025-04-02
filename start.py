# -*- coding: utf-8 -*-
"""
Script de démarrage simplifié pour l'application Flask
"""

import os
import sys

# Forcer l'encodage UTF-8 pour l'environnement Python
os.environ["PYTHONIOENCODING"] = "utf-8"

# Exécuter l'application sans charger directement les modules problématiques
if __name__ == '__main__':
    # Exécuter app.py comme un processus séparé
    os.system("python -c \"from app import app; app.run(host='0.0.0.0', port=5000, debug=True)\"")
