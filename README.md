# Projet de Calcul d'Itinéraires avec Bornes de Recharge

## Description
Ce projet est une API Flask permettant de calculer un itinéraire entre deux villes pour un véhicule électrique. L'application prend en compte l'autonomie du véhicule et ajuste l'itinéraire pour inclure des arrêts aux bornes de recharge si nécessaire.

## Fonctionnalités
- Calcul d'un itinéraire optimisé en fonction de l'autonomie du véhicule
- Recherche automatique de bornes de recharge à proximité lorsque l'autonomie atteint un seuil critique
- Intégration de l'API ORS (OpenRouteService) pour la génération des trajets
- Utilisation d'un service SOAP pour des calculs supplémentaires liés au trajet
- Documentation API avec Swagger

## Installation
### Prérequis
- Python 3.x installé
- Un environnement virtuel (recommandé)
- Fichier `.env` contenant les clés API nécessaires

### Étapes d'installation
1. **Cloner le dépôt**
   ```sh
   git clone https://github.com/votre-repo.git
   cd votre-repo
   ```

2. **Créer et activer un environnement virtuel**
   ```sh
   python -m venv venv
   source venv/bin/activate  # Sur macOS/Linux
   venv\Scripts\activate    # Sur Windows
   ```

3. **Installer les dépendances**
   ```sh
   pip install -r requirements.txt
   ```

4. **Configurer les variables d'environnement**
   Créer un fichier `.env` à la racine du projet et ajouter :
   ```ini
   ORS_API_KEY=your_openrouteservice_api_key
   X_CLIENT_ID=your_client_id
   X_APP_ID=your_app_id
   ```

5. **Lancer le serveur Flask**
   ```sh
   flask run
   ```

## Endpoints Principaux
### 1. Calcul d'un itinéraire
**POST /api/plan-route**

Corps de la requête :
```json
{
    "start_city": "Lyon",
    "end_city": "Marseille",
    "car_id": "5f043d88bc262f1627fc032b"
}
```
Réponse :
```json
{
    "distance_km": 312.5,
    "total_charge_time_min": 90,
    "stops": [
        {
            "station_name": "Total Energies",
            "adresse": "Aire de Repos A7",
            "coords": [45.75, 4.85],
            "puiss_max": 50,
            "charge_time_min": 45
        }
    ]
}
```

### 2. Calcul via service SOAP
**POST /api/travel-calculation**

Corps de la requête :
```json
{
    "distance_km": 200,
    "avg_speed_kmh": 90,
    "autonomy_km": 300,
    "charge_time_min": 120,
    "cost_per_km": 0.1
}
```

Réponse :
```json
{
    "soap_result": "Temps total estimé : 4h15, Coût estimé : 20€"
}
```

## Explication du Calcul de l'Itinéraire
1. L'API récupère les coordonnées des villes de départ et d'arrivée grâce à une fonction de géocodage.
2. Un itinéraire est généré à l'aide de l'API ORS.
3. L'autonomie du véhicule est comparée à la distance restante.
4. Lorsque l'autonomie atteint 20%, une borne de recharge est recherchée dans un rayon de 50 km.
5. Une déviation est ajoutée au trajet pour inclure cette borne.
6. Une fois chargé, le véhicule reprend son itinéraire vers la destination finale.

## Déploiement sur Azure
### Configuration GitHub Actions
Un workflow est inclus pour déployer automatiquement l'application sur Azure Static Web Apps lors d'un `push` sur la branche `fin`.

### Variables Sécurisées
Assurez-vous d'ajouter les secrets suivants dans GitHub :
- `AZURE_STATIC_WEB_APPS_API_TOKEN`
- `GITHUB_TOKEN`


## Licence
Ce projet est sous licence MIT.

