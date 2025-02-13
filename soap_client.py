from zeep import Client

SOAP_WSDL = "http://127.0.0.1:8000?wsdl"

def soap_calculate_trip(distance_km, avg_speed_kmh, autonomy_km, charge_time_min, cost_per_km):
    """
    Appelle la méthode SOAP 'calculate_trip' et renvoie la chaîne de résultat.
    """
    client = Client(SOAP_WSDL)
    response = client.service.calculate_trip(
        distance_km,
        avg_speed_kmh,
        autonomy_km,
        charge_time_min,
        cost_per_km
    )
    # `response` est le texte renvoyé par votre service,
    # par ex: "Temps total: 6h30, Coût: 43.60 € (Nombre de recharges: 1)."
    return response