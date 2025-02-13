from spyne import Application, rpc, ServiceBase, Float, Integer, String
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication


class TravelCalculatorService(ServiceBase):
    """
    Service SOAP qui calcule un temps total de trajet et un coût,
    en tenant compte de la distance, de l'autonomie et du temps de recharge.
    """

    @rpc(
        Float,  # distance (km)
        Float,  # vitesse moyenne (km/h)
        Float,  # autonomie (km)
        Float,  # temps de recharge (minutes) pour une recharge complète
        Float,  # coût par km
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

        # 1) Temps de conduite total
        drive_time_h = distance_km / avg_speed_kmh  # en heures

        # 2) Calcul du nombre « d’unités » d’autonomie utilisées
        #    Exemple : si distance=800 km et autonomie=300 km,
        #    full_segments = 2 (600 km), leftover_distance=200 km
        full_segments = int(distance_km // autonomy_km)
        leftover_distance = distance_km % autonomy_km

        if full_segments == 0:
            # Si la distance totale est inférieure ou égale à l’autonomie,
            # aucun arrêt pour recharger.
            nb_recharges = 0
            total_charge_time_min = 0
        else:
            # On sait qu’il faut au moins un (ou plusieurs) arrêts-recharge
            # pour parcourir 'distance_km' en entier.
            #
            # - Le premier « segment » est couvert par la batterie déjà pleine au départ
            # - Chaque segment d’autonomie complet suivant nécessite un arrêt
            #   pour passer de 0% à 100%.
            #
            # Par contre, si leftover_distance > 0 (c’est-à-dire qu’on dépasse juste
            # un multiple d’autonomie), on aura besoin d’une "recharge partielle"
            # pour ce dernier tronçon.
            #
            # EXEMPLE :
            #   * 800 km, autonomie=300 km
            #   * full_segments = 2 (600 km), leftover=200
            #   * => il y a 2 segments de 300 km + 1 segment de 200 km
            #   *   => 2 arrêts recharge complets pour couvrir les 2 segments complets
            #       + 1 recharge partielle (200/300) pour le leftover

            # Nombre de recharges "complètes"
            # Si leftover_distance == 0, alors on n'a pas à recharger après le dernier segment.
            if leftover_distance == 0:
                # Exemple : 600 km, autonomie=300 => pile 2 segments
                # => on a fait 2 segments mais le 2e segment se termine sur la destination,
                #    donc on ne recharge pas "après" le 2e segment.
                nb_recharges = full_segments - 1
                partial_charge_time_min = 0
            else:
                # leftover_distance > 0 => on aura un tronçon partiel à couvrir
                # => on compte 'full_segments' recharges complètes,
                #    puis 1 recharge partielle pour finir.
                nb_recharges = full_segments
                # Temps de recharge partielle : proportionnel au ratio leftover/autonomy
                partial_charge_ratio = leftover_distance / autonomy_km
                partial_charge_time_min = partial_charge_ratio * charge_time_min

            # Temps de recharge total = (nombre de recharges complètes + recharge partielle)
            total_charge_time_min = nb_recharges * charge_time_min + partial_charge_time_min

        # 3) Conversion du temps de recharge (min -> h) et addition
        total_charge_time_h = total_charge_time_min / 60.0
        total_time_h = drive_time_h + total_charge_time_h

        # 4) Calcul du coût total
        total_cost = distance_km * cost_per_km

        # 5) Mise en forme (H:MM)
        hours = int(total_time_h)
        minutes = int(round((total_time_h - hours) * 60))

        result_str = (
            f"Temps total: {hours}h{minutes:02d}, "
            f"Coût: {total_cost:.2f} € "
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
