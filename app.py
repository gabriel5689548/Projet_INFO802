import openrouteservice as ors
from openrouteservice import convert
import folium
import requests
from flask import Flask, request, render_template, jsonify
from soap_client import soap_calculate_trip
from flasgger import Swagger

app = Flask(__name__)


# 2) Config minimale pour Flasgger + Swagger UI

swagger = Swagger(app)

# ---------------------------------------------------------------------------
# Clé OpenRouteService (remplacez par la vôtre)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Exemple d'endpoint (commenté) pour récupérer la borne la plus proche
# ---------------------------------------------------------------------------
"""
@app.route('/nearest-charging-station', methods=['GET'])
def nearest_charging_station():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Paramètres lat et lon requis"}), 400

    distance_meters = 5000
    url_irve = (
        "https://opendata.reseaux-energies.fr/api/records/1.0/search/"
        "?dataset=bornes-irve"
        f"&geofilter.distance={lat},{lon},{distance_meters}"
        "&rows=1"
    )

    try:
        response = requests.get(url_irve)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

    data = response.json()

    if "records" not in data or len(data["records"]) == 0:
        return jsonify({"message": "Aucune borne trouvée à proximité"}), 404

    record = data["records"][0]
    fields = record.get("fields", {})

    station_name = fields.get("n_station")
    station_adresse = fields.get("ad_station")
    station_coords = fields.get("geo_point_borne")
    amenageur = fields.get("n_amenageur")
    type_prise = fields.get("type_prise")
    puiss_max = fields.get("puiss_max")

    result = {
        "station_name": station_name,
        "station_adresse": station_adresse,
        "station_coords": station_coords,
        "amenageur": amenageur,
        "type_prise": type_prise,
        "puiss_max": puiss_max
    }

    return jsonify(result), 200
"""

# ---------------------------------------------------------------------------
# Fonction utilitaire : Géocodage via Nominatim (OpenStreetMap)
# ---------------------------------------------------------------------------
def geocode_place(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "MyFlaskApp/1.0 (https://example.com; email@example.com)"
    }
    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return (lat, lon)
    except requests.exceptions.RequestException as e:
        print("Erreur de géocodage:", e)
        return None

# ---------------------------------------------------------------------------
# Page d'accueil : formulaire + liste des voitures
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    cars = fetch_cars()
    selected_car = None

    # Valeurs par défaut pour éviter l'erreur
    distance_km = 0.0
    autonomy_km = 0.0
    charge_time_min = 0
    soap_result_str = ""

    return render_template(
        'map_page.html',
        cars=cars,
        selected_car=selected_car,
        distance_km=distance_km,
        autonomy_km=autonomy_km,
        charge_time_min=charge_time_min,
        soap_result=soap_result_str
    )



# ---------------------------------------------------------------------------
# API Chargetrip : Récupération de la liste des véhicules
# ---------------------------------------------------------------------------
API_URL = "https://api.chargetrip.io/graphql"
HEADERS = {
    "x-client-id": "678e43d96f014f34da844c42",
    "x-app-id": "678e43d96f014f34da844c44",
    "Content-Type": "application/json",
}

query = """
query {
  carList {
    id
    make
    carModel
    battery {
      usable_kwh
      full_kwh
    }
    connectors {
      standard
      power
    }
    media {
      image {
        thumbnail_url
      }
    }
  }
}
"""


def fetch_cars():
    try:
        resp = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            return []
        cars = data.get("data", {}).get("carList", [])

        for car in cars:
            # Gestion de 'battery'
            if car.get("battery") is None:
                car["battery"] = {}
            car["battery"].setdefault("usable_kwh", 0)
            car["battery"].setdefault("full_kwh", 0)

            # Gestion de 'connectors'
            if car.get("connectors") is None or not isinstance(car["connectors"], list):
                car["connectors"] = []

            # Gestion de 'media'
            if car.get("media") is None:
                car["media"] = {}
            if not isinstance(car["media"], dict):
                car["media"] = {}

            # Gestion de 'media.image'
            if "image" not in car["media"] or not isinstance(car["media"]["image"], dict):
                car["media"]["image"] = {}

            # URL par défaut si manquante
            car["media"]["image"].setdefault("thumbnail_url", "https://via.placeholder.com/300x200")

        return cars
    except Exception as e:
        print("Erreur fetch_cars:", e)
        return []

@app.route('/api/cars', methods=['GET'])
def get_cars():
    """
    Récupération de la liste des véhicules (GraphQL)
    ---
    tags:
      - "Vehicules"
    summary: "Liste tous les véhicules depuis l'API GraphQL"
    description: "Appelle l'API Chargetrip pour récupérer la liste de voitures."
    produces:
      - "application/json"
    responses:
      200:
        description: "Liste des véhicules récupérée avec succès."
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              make:
                type: string
              carModel:
                type: string
      500:
        description: "Erreur lors de la récupération des véhicules."
    """
    cars = fetch_cars()
    if not cars:
        return jsonify({"error": "Impossible de récupérer la liste des véhicules"}), 500
    return jsonify(cars)

# ---------------------------------------------------------------------------
# Fonction pour trouver la borne la plus proche (extrait du code commenté)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Exemple d'API IRVE
# ---------------------------------------------------------------------------
@app.route('/api/charging-stations', methods=['GET'])
def find_nearest_charging_station(lat, lon, distance_meters=5000):
    """
        Récupère les bornes de recharge dans un rayon
        ---
        tags:
          - "ChargingStations"
        summary: "Récupération des bornes de recharge"
        description: "Appelle l'API IRVE pour trouver les bornes autour d'un point."
        parameters:
          - name: lat
            in: query
            type: number
            required: true
            description: "Latitude du point de départ"
          - name: lon
            in: query
            type: number
            required: true
            description: "Longitude du point de départ"
          - name: radius
            in: query
            type: integer
            required: false
            default: 5000
            description: "Rayon en mètres"
        produces:
          - "application/json"
        responses:
          200:
            description: "Liste des bornes proches."
          404:
            description: "Aucune borne trouvée."
    """
    url_irve = (
        "https://opendata.reseaux-energies.fr/api/records/1.0/search/"
        "?dataset=bornes-irve"
        f"&geofilter.distance={lat},{lon},{distance_meters}"
        "&rows=1"
    )
    try:
        response = requests.get(url_irve)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erreur IRVE : {e}")
        return None

    data = response.json()
    if "records" not in data or len(data["records"]) == 0:
        return None

    record = data["records"][0]
    fields = record.get("fields", {})
    station_name = fields.get("n_station", "Borne inconnue")
    station_addr = fields.get("ad_station", "Adresse inconnue")
    station_coords = fields.get("geo_point_borne")  # [lat, lon]
    puiss_max = fields.get("puiss_max")
    return {
        "station_name": station_name,
        "adresse": station_addr,
        "coords": station_coords,
        "puiss_max": puiss_max
    }


# ---------------------------------------------------------------------------
# Géocodage via Nominatim
# ---------------------------------------------------------------------------
def geocode_place(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "MyFlaskApp/1.0"
    }
    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return (lat, lon)
    except:
        return None

# ---------------------------------------------------------------------------
# ORS client
# ---------------------------------------------------------------------------
def ors_directions(coord_start, coord_end):
    """
    Calcule l'itinéraire entre deux points (lat, lon) via ORS (driving-car).
    Retourne le dict 'directions' complet.
    """
    client = ors.Client(key=ORS_API_KEY)
    # ORS attend (lon, lat)
    start_lonlat = (coord_start[1], coord_start[0])
    end_lonlat   = (coord_end[1], coord_end[0])
    return client.directions([start_lonlat, end_lonlat], profile='driving-car',instructions=True,language='fr')

# ---------------------------------------------------------------------------
# Calcul distance entre deux points (lon, lat)
# ---------------------------------------------------------------------------
def haversine(lon1, lat1, lon2, lat2):
    import math
    R = 6371.0
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

# ---------------------------------------------------------------------------
# Récupération de voitures (Chargetrip)
# ---------------------------------------------------------------------------
API_URL = "https://api.chargetrip.io/graphql"
HEADERS = {
    "x-client-id": "678e43d96f014f34da844c42",
    "x-app-id": "678e43d96f014f34da844c44",
    "Content-Type": "application/json",
}
query = """
query {
  carList {
    id
    make
    carModel
    battery {
      usable_kwh
      full_kwh
    }
    connectors {
      standard
      power
    }
    media {
      image {
        thumbnail_url
      }
    }
  }
}
"""
def fetch_cars():
    try:
        resp = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            return []
        return data.get("data", {}).get("carList", [])
    except:
        return []

# ---------------------------------------------------------------------------
# Page d'accueil
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
#  FONCTION "MULTI-ÉTAPES" - VRAI ITINÉRAIRE AVEC DETOUR VERS LES BORNES
# ---------------------------------------------------------------------------

@app.route('/api/plan-route', methods=['POST'])
def multi_step_route():
    """
        Calcul complet d’un itinéraire multi-étapes (HTML)
        ---
        tags:
          - "SoapCalc"
        summary: "Calcule un itinéraire (avec recharge) et retourne une page HTML avec une carte."
        consumes:
          - "application/x-www-form-urlencoded"
        parameters:
          - name: start_city
            in: formData
            type: string
            required: true
            description: "Ville de départ (ex: 'Annecy')"
          - name: end_city
            in: formData
            type: string
            required: true
            description: "Ville d'arrivée (ex: 'Paris')"
          - name: car_id
            in: formData
            type: string
            required: true
            description: "ID de la voiture (obtenu depuis /cars)"
        responses:
          200:
            description: "Page HTML contenant la carte Folium et le résumé du trajet"
          400:
            description: "Paramètres manquants, géocodage échoué, etc."
    """
    start_city = request.form.get('start_city')
    end_city = request.form.get('end_city')
    car_id = request.form.get('car_id')

    result = compute_route_data(start_city, end_city, car_id)
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    # On récupère route_segments
    route_segments = result["route_segments"]



    # Ensuite, vous appliquez la logique voulue :
    result = compute_route_data(start_city, end_city, car_id)
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    # Récupérer tout ce dont on a besoin pour la page HTML
    cars = result["cars"]
    selected_car = result["selected_car"]
    start_coords = result["start_coords"]
    end_coords   = result["end_coords"]
    stops        = result["stops"]
    polylines    = result["polylines"]
    total_distance_km = result["distance_km"]
    total_charge_time_min = result["total_charge_time_min"]
    soap_result  = result["soap_result_str"]

    # Génération de la carte Folium
    m = folium.Map(location=[start_coords[0], start_coords[1]], zoom_start=6)
    folium.Marker(
        location=start_coords,
        popup=f"Départ : {start_city}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    for segment in polylines:
        folium.PolyLine(segment, color="blue", weight=5).add_to(m)

    for st in stops:
        lat_s, lon_s = st['coords']
        folium.Marker(
            location=[lat_s, lon_s],
            popup=f"{st['station_name']} ({st['puiss_max']} kW)\nCharge: {st['charge_time_min']} min",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    folium.Marker(
        location=end_coords,
        popup=f"Arrivée : {end_city}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    return render_template(
        "map_page.html",
        map_html=m._repr_html_(),
        cars=cars,
        selected_car=selected_car,
        start_city=start_city,
        end_city=end_city,
        stops=stops,
        distance_km=total_distance_km,
        autonomy_km=selected_car['battery']['usable_kwh'] * 5,
        charge_time_str=_minutes_to_hhmm(total_charge_time_min),
        soap_result=soap_result,
        route_segments=route_segments
    )

def _minutes_to_hhmm(total_min):
    h = int(total_min // 60)
    m = int(total_min % 60)
    return f"{h}h{m:02d}"

@app.route('/api/travel-calculation', methods=['POST'])
def multi_step_route_api():
    """
        Calcul complet d’un itinéraire multi-étapes (API JSON)
        ---
        tags:
          - "PlanRoute"
        summary: "Calcule un itinéraire (avec recharge) et retourne un JSON détaillé."
        consumes:
          - "application/json"
        parameters:
          - in: body
            name: trajet
            required: true
            description: "Données du trajet"
            schema:
              type: object
              properties:
                start_city:
                  type: string
                  example: "Annecy"
                end_city:
                  type: string
                  example: "Paris"
                car_id:
                  type: string
                  example: "602546cb9ab805659a9ca0cb"
        responses:
          200:
            description: "Retourne un JSON avec la distance, le temps de charge, etc."
          400:
            description: "Erreur si la voiture est introuvable, géocodage échoué, etc."
    """
    # Lire data (JSON ou form, à vous de voir)
    data = request.get_json() or {}
    start_city = data.get('start_city')
    end_city   = data.get('end_city')
    car_id     = data.get('car_id')

    # On appelle la MÊME fonction factorisée :
    result = compute_route_data(start_city, end_city, car_id)
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "distance_km": result["distance_km"],
        "soap_result_str": result["soap_result_str"],
        "stops": result["stops"],
        "total_charge_time_min": result["total_charge_time_min"],
        "route_segments": result["route_segments"]
    })



def compute_route_data(start_city, end_city, car_id):
    """
    Cette fonction calcule le parcours multi-étapes.
    Retourne un dict avec:
      - error
      - cars
      - selected_car
      - start_coords, end_coords
      - distance_km
      - total_charge_time_min
      - stops
      - polylines
      - route_segments
      - soap_result_str
    """

    # 1) Récupération de la voiture
    cars = fetch_cars()
    selected_car = next((c for c in cars if c['id'] == car_id), None)
    if not selected_car:
        return {"error": "Voiture introuvable"}

    # Ex : 1 kWh = environ 5 km => ci-dessous:  usable_kwh * 5
    autonomy_km = selected_car['battery']['usable_kwh'] * 5
    battery_kwh = selected_car['battery']['usable_kwh']

    # 2) Géocodage des villes
    start_coords = geocode_place(start_city)  # (lat, lon)
    end_coords   = geocode_place(end_city)
    if not start_coords or not end_coords:
        return {"error": "Géocodage échoué"}

    # 3) Variables d’itinéraire
    total_distance_km = 0.0
    total_charge_time_min = 0
    stops = []
    polylines = []
    route_segments = []  # <-- liste pour stocker chaque segment (polyline + instructions)

    current_position = start_coords
    max_loops = 20

    # 4) Boucle de calcul multi-étapes
    for _ in range(max_loops):
        # Distance (current -> end)
        dist_to_end = haversine(
            current_position[1], current_position[0],
            end_coords[1], end_coords[0]
        )

        if dist_to_end <= autonomy_km:
            # Le véhicule peut atteindre la destination finale sans autre recharge

            # a) On récupère l’itinéraire complet
            route_final = ors_directions(current_position, end_coords)
            geometry = route_final['routes'][0]['geometry']
            decoded = convert.decode_polyline(geometry)

            # b) On extrait éventuellement les instructions
            segments = route_final['routes'][0].get('segments', [])
            if segments:
                steps = segments[0].get('steps', [])
            else:
                steps = []

            instructions_list = []
            for step in steps:
                instructions_list.append({
                    "instruction": step.get("instruction", ""),
                    "distance": step.get("distance", 0),
                    "duration": step.get("duration", 0),
                    "type": step.get("type", 0)
                })

            # c) On stocke la polyligne & instructions dans route_segments
            route_segments.append({
                "polyline": [(c[1], c[0]) for c in decoded['coordinates']],
                "instructions": instructions_list
            })

            # d) On stocke aussi la polyligne dans l’historique (pour Folium)
            polylines.append([(c[1], c[0]) for c in decoded['coordinates']])

            # e) On ajoute la distance
            segment_dist_m = route_final['routes'][0]['summary']['distance']
            total_distance_km += (segment_dist_m / 1000.0)

            break  # On sort de la boucle : on est arrivé
        else:
            # L’autonomie est insuffisante pour aller au bout directement
            # a) On calcule un itinéraire complet "test"
            route_test = ors_directions(current_position, end_coords)
            coords_list = convert.decode_polyline(route_test['routes'][0]['geometry'])['coordinates']

            # b) On cherche le point où l’autonomie est atteinte
            distance_acc = 0.0
            last_pt = (current_position[1], current_position[0])
            autonomy_reached_index = None

            for i in range(1, len(coords_list)):
                c_lon, c_lat = coords_list[i]
                seg_dist = haversine(last_pt[0], last_pt[1], c_lon, c_lat)
                distance_acc += seg_dist
                if distance_acc >= autonomy_km:
                    autonomy_reached_index = i
                    break
                last_pt = (c_lon, c_lat)

            if autonomy_reached_index is None:
                return {"error": "Problème de calcul d'autonomie"}

            c_lon, c_lat = coords_list[autonomy_reached_index]

            # c) On cherche une borne dans un rayon plus large, ex 50 km
            station_info = find_nearest_charging_station(c_lat, c_lon, distance_meters=50000)
            if not station_info:
                return {"error": "Impossible de trouver une borne dans un rayon de 50 km"}

            borne_lat, borne_lon = station_info['coords']
            puiss_max = station_info.get('puiss_max') or 22

            # d) On calcule le temps de charge (full, simplification)
            charge_time_min = (battery_kwh / puiss_max) * 60.0
            total_charge_time_min += charge_time_min

            # e) On calcule l’itinéraire jusqu’à la borne
            route_borne = ors_directions(current_position, (borne_lat, borne_lon))
            decoded_borne = convert.decode_polyline(route_borne['routes'][0]['geometry'])

            # f) On extrait instructions
            segments_borne = route_borne['routes'][0].get('segments', [])
            if segments_borne:
                steps_borne = segments_borne[0].get('steps', [])
            else:
                steps_borne = []

            instructions_list_borne = []
            for step in steps_borne:
                instructions_list_borne.append({
                    "instruction": step.get("instruction", ""),
                    "distance": step.get("distance", 0),
                    "duration": step.get("duration", 0),
                    "type": step.get("type", 0)
                })

            # g) On stocke polyligne + instructions pour ce segment
            route_segments.append({
                "polyline": [(c[1], c[0]) for c in decoded_borne['coordinates']],
                "instructions": instructions_list_borne
            })
            polylines.append([(c[1], c[0]) for c in decoded_borne['coordinates']])

            # h) On ajoute la distance
            segment_borne_dist_m = route_borne['routes'][0]['summary']['distance']
            total_distance_km += (segment_borne_dist_m / 1000.0)

            # i) On enregistre l’arrêt
            stops.append({
                "station_name": station_info['station_name'],
                "adresse": station_info['adresse'],
                "coords": station_info['coords'],
                "puiss_max": puiss_max,
                "charge_time_min": round(charge_time_min, 1)
            })

            # j) Mise à jour de la position
            current_position = (borne_lat, borne_lon)
    else:
        # Si on sort de la boucle par "épuisement", c’est qu’on a trop d’étapes
        return {"error": "Trop d'étapes, itinéraire trop complexe"}

    # 5) Appel du service SOAP pour calculer le temps total + coût
    soap_result_str = soap_calculate_trip(
        distance_km      = total_distance_km,
        avg_speed_kmh    = 90.0,
        autonomy_km      = autonomy_km,
        charge_time_min  = int(round(total_charge_time_min)),
        cost_per_km      = 0.10
    )

    # 6) Retour final
    return {
        "error": None,
        "cars": cars,
        "selected_car": selected_car,
        "start_coords": start_coords,
        "end_coords": end_coords,
        "distance_km": total_distance_km,
        "total_charge_time_min": total_charge_time_min,
        "stops": stops,
        "polylines": polylines,
        "route_segments": route_segments,    # <-- IMPORTANT, on a maintenant la clé
        "soap_result_str": soap_result_str
    }



# ---------------------------------------------------------------------------
# Lancement de Flask
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)