# web_app.py

from flask import Flask, request
import zeep

app = Flask(__name__)

# Page d'accueil : un simple formulaire HTML
@app.route('/', methods=['GET'])
def index():
    return '''
    <html>
    <head>
        <title>Calcul de trajet en véhicule électrique</title>
    </head>
    <body>
        <h2>Calculer un trajet en voiture électrique</h2>
        <form action="/calculate" method="post">
            <label>Distance (km): 
                <input type="text" name="distance_km">
            </label>
            <br><br>

            <label>Vitesse moyenne (km/h): 
                <input type="text" name="avg_speed_kmh">
            </label>
            <br><br>

            <label>Autonomie (km): 
                <input type="text" name="autonomy_km">
            </label>
            <br><br>

            <label>Temps de recharge (minutes): 
                <input type="text" name="charge_time_min">
            </label>
            <br><br>

            <label>Coût par km (en €): 
                <input type="text" name="cost_per_km">
            </label>
            <br><br>

            <input type="submit" value="Calculer">
        </form>
    </body>
    </html>
    '''

# Route pour gérer la soumission du formulaire
@app.route('/calculate', methods=['POST'])
def calculate():
    # Récupérer les données du formulaire
    distance_km = float(request.form['distance_km'])
    avg_speed_kmh = float(request.form['avg_speed_kmh'])
    autonomy_km = float(request.form['autonomy_km'])
    charge_time_min = int(request.form['charge_time_min'])
    cost_per_km = float(request.form['cost_per_km'])

    # Appeler le service SOAP (qui tourne sur http://127.0.0.1:8000/?wsdl)
    wsdl_url = "http://127.0.0.1:8000/?wsdl"
    client = zeep.Client(wsdl=wsdl_url)

    # Appel de la méthode "calculate_trip" définie dans travel_service.py
    result = client.service.calculate_trip(
        distance_km,
        avg_speed_kmh,
        autonomy_km,
        charge_time_min,
        cost_per_km
    )

    # Retourner le résultat dans une page HTML
    return f"""
    <html>
    <head>
        <title>Résultat</title>
    </head>
    <body>
        <h2>Résultat du calcul</h2>
        <p>{result}</p>
        <a href="/">Revenir à l'accueil</a>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Lancement de l'appli Flask
    app.run(debug=True)
