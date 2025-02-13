# routes/vehicles.py

from flask import Blueprint, jsonify
from flasgger import swag_from
from services.compute_route import fetch_cars

vehicles_bp = Blueprint('vehicles_bp', __name__)

@vehicles_bp.route('/vehicles', methods=['GET'])
@swag_from({
    'tags': ['Vehicles'],
    'summary': 'Liste des véhicules (Chargetrip)',
    'description': 'Appelle l’API GraphQL pour récupérer les voitures.',
    'responses': {
        '200': {
            'description': 'OK'
        },
        '500': {
            'description': 'Erreur'
        }
    }
})
def get_vehicles():
    cars = fetch_cars()
    if not cars:
        return jsonify({"error": "Impossible de récupérer la liste"}), 500
    return jsonify(cars), 200
