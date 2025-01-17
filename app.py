import openrouteservice as ors
from openrouteservice import convert
import folium
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Remplacez par votre clé OpenRouteService
ORS_API_KEY = "5b3ce3597851110001cf62482aeed0ceb57845adbedd1d2d70609f5e"

""""
###############################################################################
# 1) Endpoint : /nearest-charging-station
###############################################################################
@app.route('/nearest-charging-station', methods=['GET'])
def nearest_charging_station():

    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return jsonify({"error": "Paramètres lat et lon requis"}), 400

    # On peut définir un rayon de recherche (en mètres)
    distance_meters = 5000

    # Construction de la requête à l'API IRVE
    # Doc : https://opendata.reseaux-energies.fr/explore/dataset/bornes-irve/api/
    url_irve = (
        "https://opendata.reseaux-energies.fr/api/records/1.0/search/"
        "?dataset=bornes-irve"
        f"&geofilter.distance={lat},{lon},{distance_meters}"
        "&rows=1"  # On ne récupère qu'un seul résultat (le plus proche)
    )

    try:
        response = requests.get(url_irve)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

    data = response.json()

    # Vérification qu'on a bien un record
    if "records" not in data or len(data["records"]) == 0:
        return jsonify({"message": "Aucune borne trouvée à proximité"}), 404

    record = data["records"][0]
    fields = record.get("fields", {})

    # Les champs varient parfois : vérifiez la structure renvoyée par l'API
    # geo_point_borne ou coordonneesXY ou ylatlong...
    # On essaye plusieurs clés possibles :
    station_name = fields.get("n_station")       # Nom complet
    station_adresse = fields.get("ad_station")   # Adresse
    station_coords = fields.get("geo_point_borne")
    amenageur = fields.get("n_amenageur")       # "TOTAL MARKETING FRANCE"
    type_prise = fields.get("type_prise")       # "EF"
    puiss_max = fields.get("puiss_max")

    # coords peut être [lat, lon] ou [lon, lat]. On vérifie :
    # - Souvent, geo_point_borne renvoie [lat, lon]
    #   => si la borne est à Paris, geo_point_borne ~ [48.8566, 2.3522]
    # - coordonneesXY renvoie parfois [lon, lat]
    #   => ~ [2.3522, 48.8566]
    #
    # A vous de voir selon la doc, ou faire un test print(coords) pour ajuster.
    # Pour l'exemple, on suppose geo_point_borne = [lat, lon].

    result = {
        "station_name": station_name,
        "station_adresse": station_adresse,
        "station_coords": station_coords,  # On vous laisse vérifier le sens [lat, lon]
        "amenageur": amenageur,
        "type_prise": type_prise,
        "puiss_max": puiss_max
    }

    return jsonify(result), 200
"""
###############################################################################
# 2) Endpoint : /route-map
###############################################################################
@app.route('/route-map', methods=['GET'])
def route_map():
    """
    Affiche une carte Folium avec l'itinéraire entre un point A et un point B.
    Exemple d'appel :
      http://127.0.0.1:5000/route-map?start_lat=48.8566&start_lon=2.3522&end_lat=48.8584&end_lon=2.2945
    """

    # Lecture des paramètres
    start_lat = request.args.get('start_lat', type=float)
    start_lon = request.args.get('start_lon', type=float)
    end_lat   = request.args.get('end_lat',   type=float)
    end_lon   = request.args.get('end_lon',   type=float)

    if not all([start_lat, start_lon, end_lat, end_lon]):
        return jsonify({"error": "Paramètres requis : start_lat, start_lon, end_lat, end_lon"}), 400

    # Initialisation du client OpenRouteService
    client = ors.Client(key=ORS_API_KEY)

    # Les coordonnées (lon, lat) pour openrouteservice
    coords = ((start_lon, start_lat), (end_lon, end_lat))

    try:
        # Appel à l'API Directions
        directions = client.directions(coords, profile='driving-car')

        # Récupération de la géométrie encodée (polyline)
        geometry = directions['routes'][0]['geometry']
        # Décodage en liste de points [lat, lon]
        decoded = convert.decode_polyline(geometry)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Création d’une carte Folium centrée sur le point de départ
    m = folium.Map(location=[start_lat, start_lon], zoom_start=14)

    # Ajout d’un marker pour le départ
    folium.Marker(
        [start_lat, start_lon],
        popup="Départ",
        icon=folium.Icon(color='green')
    ).add_to(m)

    # Ajout d’un marker pour l’arrivée
    folium.Marker(
        [end_lat, end_lon],
        popup="Arrivée",
        icon=folium.Icon(color='red')
    ).add_to(m)

    # Tracer la route (liste de [lat, lon]) => attention : folium attend (lat, lon)
    folium.PolyLine(
        locations=decoded['coordinates'],
        weight=5,
        color='blue',
        opacity=0.8
    ).add_to(m)

    # Retourne le rendu HTML de la carte
    return m._repr_html_()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
