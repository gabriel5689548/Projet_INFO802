# routes/soap.py

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from services.soap import soap_calculate_trip  # client Zeep qui appelle le service

soap_bp = Blueprint('soap_bp', __name__)

@soap_bp.route('/travel-calculation', methods=['POST'])
@swag_from({
    'tags': ['SoapCalc'],
    'summary': 'Calcul via service SOAP local',
    'consumes': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'distance_km': {'type': 'number', 'example': 200},
                    'avg_speed_kmh': {'type': 'number', 'example': 90},
                    'autonomy_km': {'type': 'number', 'example': 300},
                    'charge_time_min': {'type': 'number', 'example': 120},
                    'cost_per_km': {'type': 'number', 'example': 0.1}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Temps total et coût calculés'
        }
    }
})
def soap_calc():
    """Endpoint qui appelle calculate_trip via SOAP"""
    data = request.get_json() or {}
    distance_km = data.get('distance_km', 200)
    avg_speed   = data.get('avg_speed_kmh', 90)
    autonomy    = data.get('autonomy_km', 300)
    charge_min  = data.get('charge_time_min', 120)
    cost_km     = data.get('cost_per_km', 0.1)

    # On appelle le service SOAP
    soap_response = soap_calculate_trip(distance_km, avg_speed, autonomy, charge_min, cost_km)

    return jsonify({"soap_result": soap_response})
