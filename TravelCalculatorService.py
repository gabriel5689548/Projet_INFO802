# travel_service.py
from spyne import Application, rpc, ServiceBase, Float, Integer, String
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


class TravelCalculatorService(ServiceBase):
    """
    Service SOAP qui calcule un temps total de trajet et un coût,
    en tenant compte de la distance, de l'autonomie et du temps de recharge.
    """

    @rpc(
        Float,    # distance (km)
        Float,    # vitesse moyenne (km/h)
        Float,    # autonomie (km)
        Integer,  # temps de recharge (minutes) pour une recharge complète
        Float,    # coût par km
        _returns=String
    )
    def calculate_trip(
        ctx,
        distance_km,
        avg_speed_kmh,
        autonomy_km,
        charge_time_min,
        cost_per_km
    ):
        """
        Calcule et renvoie sous forme de texte le temps total et le coût du trajet.

        distance_km : distance totale (km)
        avg_speed_kmh : vitesse moyenne (km/h)
        autonomy_km : autonomie du véhicule (km)
        charge_time_min : temps de recharge complet (minutes)
        cost_per_km : coût par km
        """

        # 1) Calcul du temps de conduite
        #    Temps de conduite = distance / vitesse
        drive_time_h = distance_km / avg_speed_kmh  # en heures

        # 2) Calcul du nombre de recharges nécessaires
        #    Si l’autonomie est insuffisante pour la distance totale,
        #    on estime combien de fois il faudra recharger.

        # Nombre de recharges nécessaires (entier)
        distance_restante = max(0, distance_km - autonomy_km)
        if distance_restante <= 0:
            nb_recharges = 0  # Pas besoin de recharger
        else:
            nb_recharges = int((distance_restante - 1) // autonomy_km + 1)

        # 3) Calcul du temps total de recharge
        #    nb_recharges * charge_time_min (en minutes),
        #    puis conversion en heures pour l’addition
        total_charge_time_h = (nb_recharges * charge_time_min) / 60.0  # en heures

        # 4) Temps total (heures)
        total_time_h = drive_time_h + total_charge_time_h

        # 5) Calcul du coût total
        total_cost = distance_km * cost_per_km

        # 6) Mise en forme de la réponse
        #    On formate les heures/minutes pour être plus lisible
        hours = int(total_time_h)
        minutes = int((total_time_h - hours) * 60)

        result_str = (
            f"Temps total: {hours}h{minutes:02d}, "
            f"Coût: {total_cost:.2f} € "
            f"(Nombre de recharges: {nb_recharges})."
        )
        return result_str


# Configuration de l’application SOAP
application = Application(
    [TravelCalculatorService],
    tns='spyne.examples.travel.soap',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

# Application WSGI
wsgi_application = WsgiApplication(application)

# Point d'entrée
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print("Lancement du service sur http://127.0.0.1:8000")
    server = make_server('127.0.0.1', 8000, wsgi_application)
    server.serve_forever()
