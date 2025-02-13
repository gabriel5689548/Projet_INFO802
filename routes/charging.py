from flask import Blueprint, request, jsonify
from flasgger import swag_from
from services.compute_route import find_nearest_charging_station

charging_bp = Blueprint('charging_bp', __name__)

@charging_bp.route('/charging-stations', methods=['GET'])
@swag_from({
    'tags': ['ChargingStations'],
    'summary': 'Récupération de bornes IRVE',
    'parameters': [
        {
            'name': 'lat',
            'in': 'query',
            'type': 'number',
            'required': True,
            'description': 'Latitude'
        },
        {
            'name': 'lon',
            'in': 'query',
            'type': 'number',
            'required': True,
            'description': 'Longitude'
        },
        {
            'name': 'radius',
            'in': 'query',
            'type': 'integer',
            'default': 5000,
            'description': 'Rayon en mètres'
        }
    ],
    'responses': {
        '200': {
            'description': 'OK'
        },
        '404': {
            'description': 'Aucune borne'
        }
    }
})
def charging_stations():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 5000, type=int)

    if lat is None or lon is None:
        return jsonify({"error": "lat/lon requis"}), 400

    station = find_nearest_charging_station(lat, lon, radius)
    if not station:
        return jsonify({"error": "Aucune borne trouvée"}), 404

    return jsonify(station), 200
