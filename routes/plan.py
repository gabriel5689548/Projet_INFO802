# routes/plan.py

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from services.compute_route import compute_route_data
import logging
logging.basicConfig(level=logging.DEBUG)

plan_bp = Blueprint('plan_bp', __name__)

@plan_bp.route('/plan-route', methods=['POST'])
@swag_from({
    'tags': ['PlanRoute'],
    'summary': 'Calcule un itinéraire complet avec arrêts de recharge et informations SOAP',
    'consumes': ['application/json'],
    'parameters': [
        {
            'in': 'body',
            'name': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'start_city': {'type': 'string', 'example': 'Lyon'},
                    'end_city': {'type': 'string', 'example': 'Marseille'},
                    'car_id': {'type': 'string', 'example': '5f043d88bc262f1627fc032b'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'Données complètes du trajet',
            'schema': {
                'type': 'object',
                'properties': {
                    'distance_km': {'type': 'number', 'example': 312.5},
                    'total_charge_time_min': {'type': 'number', 'example': 90},
                    'stops': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'station_name': {'type': 'string', 'example': 'Total Energies'},
                                'adresse': {'type': 'string', 'example': 'Aire de Repos A7'},
                                'coords': {'type': 'array', 'items': {'type': 'number'}},
                                'puiss_max': {'type': 'number', 'example': 50},
                                'charge_time_min': {'type': 'number', 'example': 45}
                            }
                        }
                    },
                    'polylines': {
                        'type': 'array',
                        'items': {
                            'type': 'array',
                            'items': {'type': 'array', 'items': {'type': 'number'}}
                        }
                    }
                }
            }
        }
    }
})
def plan_route():
    logging.debug("🔍 Requête reçue pour /plan-route")

    
    data = request.get_json() or {}
    logging.debug(f"📦 Données reçues: {data}")
    start_city = data.get('start_city')
    end_city   = data.get('end_city')
    car_id     = data.get('car_id')

    if not start_city or not end_city or not car_id:
        return jsonify({"error": "Les paramètres start_city, end_city et car_id sont obligatoires"}), 400

    # Calcul complet de l'itinéraire
    logging.debug("🔄 Appel à compute_route_data()")
    result = compute_route_data(start_city, end_city, car_id)

    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    # Retourne toutes les infos nécessaires pour l'API
    logging.debug("✅ Réponse envoyée avec succès")
    return jsonify(result), 200
