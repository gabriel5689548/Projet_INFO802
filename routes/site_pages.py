# routes/site_pages.py
from flask import Blueprint, render_template, request
from services.compute_route import fetch_cars, compute_route_data
import folium

site_bp = Blueprint("site_bp", __name__)

@site_bp.route("/")  # => GET "/"
def home():
    # On affiche la page map_page.html en "mode vide"
    cars = fetch_cars()
    return render_template(
        "map_page.html",
        cars=cars,
        selected_car=None,
        distance_km=0.0,
        autonomy_km=0.0,
        charge_time_str="0h00",
        soap_result="",
        map_html=None,
        start_city="",
        end_city=""
    )

@site_bp.route("/multi-step-route", methods=["POST"])
def multi_step_route():
    """
    Route HTML qui génère un itinéraire et renvoie map_page.html
    """
    start_city = request.form.get('start_city')
    end_city   = request.form.get('end_city')
    car_id     = request.form.get('car_id')

    # 1) Calcul multi-étapes
    result = compute_route_data(start_city, end_city, car_id)
    if result.get("error"):
        return f"Erreur: {result['error']}", 400

    result = compute_route_data(start_city, end_city, car_id)
    polylines = result["polylines"]
    stops = result["stops"]

    # 2) Récupérer les infos
    cars          = result["cars"]
    selected_car  = result["selected_car"]
    start_coords  = result["start_coords"]
    end_coords    = result["end_coords"]
    distance_km   = result["distance_km"]
    autonomy_km   = selected_car["battery"]["usable_kwh"] * 5 if selected_car else 0
    total_charge_time_min = result["total_charge_time_min"]
    # Ex : convertir total_charge_time_min en "HhMM"
    heures = int(total_charge_time_min // 60)
    minutes = int(total_charge_time_min % 60)
    charge_time_str = f"{heures}h{minutes:02d}"
    soap_result   = result["soap_result_str"]

    # 3) Générer la carte Folium
    m = folium.Map(location=start_coords, zoom_start=6)
    folium.Marker(start_coords, popup="Départ", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker(end_coords,   popup="Arrivée", icon=folium.Icon(color='red')).add_to(m)
    for segment in polylines:
        folium.PolyLine(segment, color="blue", weight=5).add_to(m)

    for st in stops:
        lat_s, lon_s = st["coords"]  # [lat, lon]
        name = st["station_name"]
        folium.Marker(
            [lat_s, lon_s],
            popup=f"{name} ({st['puiss_max']} kW)\nCharge: {st['charge_time_min']} min",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    map_html = m._repr_html_()



    # 4) Renvoi map_page.html
    return render_template(
        "map_page.html",
        cars=cars,
        selected_car=selected_car,
        distance_km=distance_km,
        autonomy_km=autonomy_km,
        charge_time_str=charge_time_str,
        soap_result=soap_result,
        map_html=map_html,
        start_city=start_city,
        end_city=end_city
    )
