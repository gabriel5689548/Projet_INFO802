from flask import Flask
from flasgger import Swagger
from config import SWAGGER_CONFIG

def create_app():
    app = Flask(__name__)
    app.config['SWAGGER'] = SWAGGER_CONFIG
    swagger = Swagger(app)

    # Import des routes "HTML"
    from routes.site_pages import site_bp
    app.register_blueprint(site_bp)  # => "/" et "/multi-step-route"

    # Import des routes "API" JSON
    from routes.vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp, url_prefix='/api')

    from routes.charging import charging_bp
    app.register_blueprint(charging_bp, url_prefix='/api')

    from routes.plan import plan_bp
    app.register_blueprint(plan_bp, url_prefix='/api')

    from routes.soap import soap_bp
    app.register_blueprint(soap_bp, url_prefix='/api')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
