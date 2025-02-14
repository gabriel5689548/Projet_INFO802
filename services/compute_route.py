# services/compute_route.py

import requests
import math
from services.geocode import geocode_place
from services.ors_client import ors_directions
from services.soap import soap_calculate_trip
from openrouteservice import convert
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Récupérer les clés API
ORS_API_KEY = os.getenv("ORS_API_KEY")
IRVE_API_URL = os.getenv("IRVE_API_URL")
X_CLIENT_ID = os.getenv("X_CLIENT_ID")
X_APP_ID = os.getenv("X_APP_ID")


def haversine(lon1, lat1, lon2, lat2):
    R = 6371.0
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

def fetch_cars():
    # Exemple minimal
    API_URL = "https://api.chargetrip.io/graphql"
    HEADERS = {
        "x-client-id": "X_CLIENT_ID",
        "x-app-id": "X_APP_ID",
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
        }
        media {
          image {
            thumbnail_url
          }
        }
      }
    }
    """
    try:
        resp = requests.post(API_URL, json={"query": query}, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            return []
        return data["data"]["carList"]
    except:
        return []

def find_nearest_charging_station(lat, lon, distance_meters=5000):
    # Exemple simple
    url_irve = (
        "https://opendata.reseaux-energies.fr/api/records/1.0/search/"
        "?dataset=bornes-irve"
        f"&geofilter.distance={lat},{lon},{distance_meters}"
        "&rows=1"
    )
    try:
        response = requests.get(url_irve)
        response.raise_for_status()
        data = response.json()
    except:
        return None

    if "records" not in data or len(data["records"]) == 0:
        return None

    record = data["records"][0]
    fields = record.get("fields", {})
    return {
        "station_name": fields.get("n_station", "Inconnue"),
        "adresse": fields.get("ad_station", ""),
        "coords": fields.get("geo_point_borne"),
        "puiss_max": fields.get("puiss_max", 22)
    }


def compute_route_data(start_city, end_city, car_id):
    stops = []
    cars = fetch_cars()
    selected_car = next((c for c in cars if c['id'] == car_id), None)
    if not selected_car:
        return {"error": "Voiture introuvable"}

    autonomy_km = selected_car['battery']['usable_kwh'] * 5 # Calcul de l'autonomie max (ex: 60 kWh * 5 = 300 km)
    battery_kwh = selected_car['battery']['usable_kwh'] # Capacité totale de la batterie

    start_coords = geocode_place(start_city)
    end_coords   = geocode_place(end_city)
    if not start_coords or not end_coords:
        return {"error": "Géocodage échoué"}

    total_distance_km = 0.0
    total_charge_time_min = 0
    polylines = []
    current_position = start_coords
    max_loops = 20

    for _ in range(max_loops):
        dist_to_end = haversine(
            current_position[1], current_position[0],
            end_coords[1], end_coords[0]
        )
        if dist_to_end <= autonomy_km:
            # Dernière portion vers l'arrivée
            route_final = ors_directions(current_position, end_coords)
            geometry = route_final['routes'][0]['geometry']
            decoded = convert.decode_polyline(geometry)
            polylines.append([(pt[1], pt[0]) for pt in decoded['coordinates']])
            total_distance_km += route_final['routes'][0]['summary']['distance'] / 1000.0
            instructions = [
                {
                    "text": step["instruction"],
                    "distance_m": step["distance"],
                    "duration_s": step["duration"]
                }
                for step in route_final['routes'][0]['segments'][0]['steps']
            ]
            break
        else:
            # On ne peut pas atteindre la destination en une seule charge
            route_test = ors_directions(current_position, end_coords)
            coords_list = convert.decode_polyline(route_test['routes'][0]['geometry'])['coordinates']

            distance_acc = 0.0
            last_pt = (current_position[1], current_position[0])
            autonomy_reached_index = None

            for i in range(1, len(coords_list)):
                c_lon, c_lat = coords_list[i]
                seg_dist = haversine(last_pt[0], last_pt[1], c_lon, c_lat)
                distance_acc += seg_dist
                if distance_acc >= autonomy_km * 0.80:
                    autonomy_reached_index = i
                    break
                last_pt = (c_lon, c_lat)

            if autonomy_reached_index is None:
                return {"error": "Erreur calcul autonomie"}

            c_lon, c_lat = coords_list[autonomy_reached_index]

            # Trouver une borne proche du point d'autonomie
            station_info = find_nearest_charging_station(c_lat, c_lon, distance_meters=50000)
            if not station_info:
                return {"error": "Aucune borne trouvée"}

            borne_lat, borne_lon = station_info['coords']
            puiss_max = station_info.get('puiss_max') or 22

            # Temps de charge approximatif
            charge_time_min = (battery_kwh / puiss_max) * 60.0
            total_charge_time_min += charge_time_min

            # Itinéraire jusqu'à la borne
            route_borne = ors_directions(current_position, (borne_lat, borne_lon))
            decoded_borne = convert.decode_polyline(route_borne['routes'][0]['geometry'])
            polylines.append([(c[1], c[0]) for c in decoded_borne['coordinates']])

            # Distance accumulée
            segment_borne_dist_m = route_borne['routes'][0]['summary']['distance']
            total_distance_km += (segment_borne_dist_m / 1000.0)

            # Ajouter la station
            stops.append({
                "station_name": station_info['station_name'],
                "adresse": station_info['adresse'],
                "coords": station_info['coords'],
                "puiss_max": puiss_max,
                "charge_time_min": round(charge_time_min, 1)
            })

            current_position = (borne_lat, borne_lon)

    else:
        return {"error": "Trop d'étapes, itinéraire trop complexe"}

    # Calcul via SOAP
    soap_result_str = soap_calculate_trip(
        distance_km=total_distance_km,
        avg_speed_kmh=90.0,
        autonomy_km=autonomy_km,
        charge_time_min=int(round(total_charge_time_min)),
        cost_per_km=0.1
    )

    return {
        "error": None,
        "cars": cars,
        "selected_car": selected_car,
        "start_coords": start_coords,
        "end_coords": end_coords,
        "distance_km": total_distance_km,
        "total_charge_time_min": total_charge_time_min,
        "stops": stops,
        "instructions": instructions,
        "polylines": polylines,
        "soap_result_str": soap_result_str
    }
