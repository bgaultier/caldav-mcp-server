# Serveur MCP CalDAV

Un serveur Model Context Protocol (MCP) permettant d'interagir avec des calendriers CalDAV. Ce serveur permet aux assistants IA de gérer les événements de calendrier, lister les calendriers et gérer les invitations aux réunions.

![Capture d'écran VS Code du serveur MCP CalDAV](https://raw.githubusercontent.com/bgaultier/caldav-mcp-server/capture_continue.png)

## Fonctionnalités

- **Lister les calendriers** : Récupérer tous les calendriers disponibles depuis votre compte CalDAV
- **Créer des événements** : Créer des événements de calendrier avec prise en charge de :
  - Détails de l'événement (titre, description, lieu)
  - Gestion du temps avec gestion automatique des fuseaux horaires
  - Invitations aux réunions avec demandes de RSVP
- **Rechercher des événements** : Rechercher des événements dans une plage horaire spécifique
- **Heure actuelle** : Obtenir l'heure système locale actuelle pour les calculs de dates

## Prérequis

- Python 3.8+
- Un service de calendrier compatible CalDAV (par ex. iCloud, Google Calendar, Nextcloud)

## Installation

1. Cloner ce dépôt
2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Créer un fichier `.env` avec vos identifiants CalDAV :
```env
CALDAV_URL=https://votre-serveur-caldav.fr
CALDAV_USERNAME=votre-nom-utilisateur
CALDAV_PASSWORD=votre-mot-de-passe
```

Pour les personnels de l'IMT :
```env
CALDAV_URL=https://z.imt.fr/
CALDAV_USERNAME=prenom.nom@imt-atlantique.fr
CALDAV_PASSWORD=votre-mot-de-passe
```

## Utilisation

Lancer le serveur :
```bash
python app.py
```

## Outils disponibles

### `get_current_time()`
Retourne l'heure système locale actuelle aux formats lisible et ISO 8601 (YYYY-MM-DDTHH:MM:SS).

### `list_calendars()`
Liste tous les calendriers disponibles avec leurs noms, URLs et identifiants.

### `create_event(calendar_name, summary, start_time, end_time, attendees=[], description="", location="")`
Crée un nouvel événement de calendrier avec des participants et invitations optionnels.

**Paramètres :**
- `calendar_name` : Nom du calendrier cible
- `summary` : Titre de l'événement
- `start_time` : Heure de début au format ISO 8601 (par ex. '2023-12-01T14:30:00')
- `end_time` : Heure de fin au format ISO 8601
- `attendees` : Liste d'adresses email à inviter (optionnel)
- `description` : Description de l'événement (optionnel)
- `location` : Lieu de l'événement (optionnel)

### `get_events(calendar_name, start_time, end_time)`
Récupère les événements dans une plage horaire spécifiée.

## Détails techniques

- Utilise la bibliothèque `caldav` pour la communication avec le protocole CalDAV
- Utilise `icalendar` pour la conformité RFC 5545 et les invitations aux réunions
- Gestion automatique des fuseaux horaires pour une planification cohérente des événements
- Framework FastMCP pour l'implémentation du protocole MCP

## Licence

GPL-3.0