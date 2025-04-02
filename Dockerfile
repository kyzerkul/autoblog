# Image de base Python
FROM python:3.11-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des répertoires nécessaires
RUN mkdir -p templates services utils tests

# Exposition du port
EXPOSE 5000

# Variables d'environnement
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Commande de démarrage
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"] 