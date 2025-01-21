import openrouteservice as ors
from openrouteservice import convert
import folium
import requests
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Clé OpenRouteService (remplacez par la vôtre)
# ---------------------------------------------------------------------------
ORS_API_KEY = "5b3ce3597851110001cf62482aeed0ceb57845adbedd1d2d70609f5e"

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
    # Récupération des voitures depuis l'API
    cars = fetch_cars()
    if not cars:
        cars = []  # Si aucune voiture, on affiche une liste vide

    # Renvoi du template avec les voitures incluses
    return render_template('index.html', cars=cars)

# ---------------------------------------------------------------------------
# Exemple d'affichage simple de la route (sans arrêts) - Optionnel
# ---------------------------------------------------------------------------
@app.route('/show-route', methods=['POST'])
def show_route():
    start_city = request.form['start_city']
    end_city = request.form['end_city']

    # Géocodage
    start_coords = geocode_place(start_city)  # (lat, lon)
    end_coords = geocode_place(end_city)      # (lat, lon)
    if not start_coords:
        return jsonify({"error": f"Ville introuvable : {start_city}"}), 400
    if not end_coords:
        return jsonify({"error": f"Ville introuvable : {end_city}"}), 400

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords

    client = ors.Client(key=ORS_API_KEY)
    coords = ((start_lon, start_lat), (end_lon, end_lat))

    try:
        directions = client.directions(coords, profile='driving-car')
        geometry = directions['routes'][0]['geometry']
        decoded = convert.decode_polyline(geometry)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    m = folium.Map(location=[start_lat, start_lon], zoom_start=6)

    # Marqueur départ
    folium.Marker(
        [start_lat, start_lon],
        popup=f"Départ : {start_city}",
        icon=folium.Icon(color='green')
    ).add_to(m)

    # Marqueur arrivée
    folium.Marker(
        [end_lat, end_lon],
        popup=f"Arrivée : {end_city}",
        icon=folium.Icon(color='red')
    ).add_to(m)

    # Tracé de la route
    coords_for_folium = [(latlon[1], latlon[0]) for latlon in decoded['coordinates']]
    folium.PolyLine(
        locations=coords_for_folium,
        weight=5,
        color='blue',
        opacity=0.8
    ).add_to(m)

    map_html = m._repr_html_()
    return render_template('route_map.html',
                           map_html=map_html,
                           start_city=start_city,
                           end_city=end_city)

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
        response = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        print("Statut HTTP :", response.status_code)
        print("Réponse brute :", response.text)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print("Erreur GraphQL :", data["errors"])
            return None

        cars = data.get("data", {}).get("carList", [])
        return cars
    except requests.exceptions.RequestException as e:
        print("Erreur de requête :", e)
        return None

@app.route('/cars', methods=['GET'])
def get_cars():
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
def find_nearest_charging_station(lat, lon, distance_meters=5000):
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
    return {
        "station_name": station_name,
        "adresse": station_addr,
        "coords": station_coords
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
    return client.directions([start_lonlat, end_lonlat], profile='driving-car')

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
@app.route('/multi-step-route', methods=['POST'])
def multi_step_route():
    """
    Calcule un itinéraire multi-étapes :
    - Recalcule à chaque fois un segment pour aller jusqu'à la borne choisie,
    - Continue ainsi jusqu'à la destination finale.
    """
    start_city = request.form['start_city']
    end_city   = request.form['end_city']
    car_id     = request.form['car_id']

    # 1) Récup voiture => calcul autonomie
    cars = fetch_cars()
    selected_car = next((c for c in cars if c['id'] == car_id), None)
    if not selected_car:
        return jsonify({"error": "Voiture introuvable"}), 400

    # Hypothèse : 1 kWh = 5 km
    autonomy_km = selected_car['battery']['usable_kwh'] * 5

    # 2) Géocodage
    start_coords = geocode_place(start_city)  # (lat, lon)
    end_coords   = geocode_place(end_city)    # (lat, lon)
    if not start_coords or not end_coords:
        return jsonify({"error": "Géocodage échoué"}), 400

    # 3) Liste de polylines (chaque segment)
    #    + Bornes (pour marquer sur la carte)
    polylines = []  # chaque élément = liste de [lat, lon]
    stops    = []   # liste des bornes rencontrées (et départ / arrivée)

    current_position = start_coords  # (lat, lon)
    max_loops = 20  # sécurité : on évite de boucler infiniment si on ne trouve pas de borne

    for _ in range(max_loops):
        # Distance (current -> end)
        dist_to_end = haversine(current_position[1], current_position[0],
                                end_coords[1], end_coords[0])

        if dist_to_end <= autonomy_km:
            # On peut aller directement jusqu'à la fin
            route_final = ors_directions(current_position, end_coords)
            geometry = route_final['routes'][0]['geometry']
            decoded  = convert.decode_polyline(geometry)
            segment_points = [(c[1], c[0]) for c in decoded['coordinates']]  # (lat, lon)
            polylines.append(segment_points)
            # On sort de la boucle
            break
        else:
            # On ne peut pas atteindre la fin directement
            # => On calcule l'itinéraire current -> end juste pour savoir
            #    où on tombe en panne.
            route_test = ors_directions(current_position, end_coords)
            geometry   = route_test['routes'][0]['geometry']
            decoded    = convert.decode_polyline(geometry)
            coords_list = decoded['coordinates']  # liste de [lon, lat]
            distance_acc = 0.0
            last_pt = (current_position[1], current_position[0])  # (lon, lat) pour la distance
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
                # bizarre : on n'a pas dépassé l'autonomie,
                # mais on est dans le else -> on retente ?
                # On sort pour éviter la boucle infinie
                return jsonify({"error": "Problème de calcul d'autonomie"}), 500

            # Point où on atteint l'autonomie
            # On cherche une borne proche de ce point
            c_lon, c_lat = coords_list[autonomy_reached_index]
            station_info = find_nearest_charging_station(c_lat, c_lon, distance_meters=20000)
            if not station_info:
                # pas de borne trouvée
                return jsonify({"error": "Impossible de trouver une borne dans un rayon de 20 km"}), 400

            # On a trouvé une borne => on calcule le vrai itinéraire current -> borne
            borne_lat, borne_lon = station_info['coords']  # [lat, lon]
            route_borne = ors_directions(current_position, (borne_lat, borne_lon))
            geom_borne   = route_borne['routes'][0]['geometry']
            decoded_borne = convert.decode_polyline(geom_borne)
            segment_borne_points = [(c[1], c[0]) for c in decoded_borne['coordinates']]  # (lat, lon)
            polylines.append(segment_borne_points)

            # On ajoute la borne dans la liste des stops
            stops.append({
                "station_name": station_info['station_name'],
                "adresse": station_info['adresse'],
                "coords": station_info['coords']  # [lat, lon]
            })

            # On met à jour current_position
            current_position = (borne_lat, borne_lon)

    else:
        # si on sort de la boucle for _ in range(max_loops) par 'épuisement',
        # c'est qu'on a fait 20 étapes, c'est suspect
        return jsonify({"error": "Trop d'étapes, itinéraire trop complexe"}), 400

    # 4) On construit la carte Folium
    m = folium.Map(location=[start_coords[0], start_coords[1]], zoom_start=6)

    # Marqueur de départ
    folium.Marker(
        location=[start_coords[0], start_coords[1]],
        popup=f"Départ : {start_city}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    # On dessine chaque segment
    for segment in polylines:
        folium.PolyLine(segment, color="blue", weight=5).add_to(m)

    # Marqueurs des bornes
    for st in stops:
        lat_s, lon_s = st['coords']
        folium.Marker(
            location=[lat_s, lon_s],
            popup=f"{st['station_name']}\n{st['adresse']}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    # Marqueur d'arrivée
    folium.Marker(
        location=[end_coords[0], end_coords[1]],
        popup=f"Arrivée : {end_city}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    map_html = m._repr_html_()

    # On peut éventuellement renvoyer la liste des stops pour info
    return render_template("route_map.html",
                           map_html=map_html,
                           start_city=start_city,
                           end_city=end_city,
                           stops=stops)

# ---------------------------------------------------------------------------
# Lancement de Flask
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)