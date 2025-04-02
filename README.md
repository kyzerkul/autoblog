# YouTube Article Generator

A Flask web application that automatically generates blog articles from YouTube videos.

## Features

- YouTube video transcript extraction
- Structured article generation via Mistral API
- Autopilot mode for automatic monitoring of YouTube channels
- Project management for multiple WordPress sites
- Intuitive user interface
- REST API for external integrations

## Requirements

- Python 3.11+
- Mistral API key
- WordPress site with REST API access
- Supabase account for database

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kyzerkul/autoblog.git
cd autoblog
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with the following content:
```
MISTRAL_API_KEY=your_mistral_api_key
WORDPRESS_URL=your_wordpress_url
WORDPRESS_USERNAME=your_wordpress_username
WORDPRESS_APP_PASSWORD=your_wordpress_app_password
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser at http://localhost:5000

3. Configure your projects with WordPress sites and YouTube channels

4. Start monitoring YouTube channels to generate articles automatically

## Project Management

- Create multiple projects, each with its own WordPress site
- Add multiple YouTube channels to each project
- Control monitoring status of each channel independently
- View published articles for each project

## API Endpoints

### Génération d'article
```
POST /api/generate-article
Content-Type: application/json

{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

### Mode Autopilote
```
POST /api/autopilot/start
Content-Type: application/json

{
    "channel_id": "CHANNEL_ID"
}
```

## Structure du Projet

```
.
├── app.py                 # Application principale Flask
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration Docker
├── templates/            # Templates HTML
├── services/            # Services métier
├── utils/               # Utilitaires
└── tests/               # Tests unitaires
```

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## License

MIT License - voir le fichier LICENSE pour plus de détails. 