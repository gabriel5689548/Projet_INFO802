# services/soap.py
from zeep import Client

WSDL_URL = "http://127.0.0.1:8000?wsdl"

def soap_calculate_trip(distance_km, avg_speed_kmh, autonomy_km, charge_time_min, cost_per_km):
    """
    Appelle le service SOAP local et renvoie la chaîne de résultat.
    """
    client = Client(WSDL_URL)
    response = client.service.calculate_trip(
        distance_km,
        avg_speed_kmh,
        autonomy_km,
        charge_time_min,
        cost_per_km
    )
    return response
