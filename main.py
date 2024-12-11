from flask import Flask, jsonify
from routes.user_routes import user_routes
from routes.subscription_routes import subscription_routes
from routes.analytics_routes import analytics_routes
from db import get_db_connection

app = Flask(__name__)

# Registra las rutas
app.register_blueprint(user_routes)
app.register_blueprint(subscription_routes)
app.register_blueprint(analytics_routes)

@app.route('/test_db_connection', methods=['GET'])
def test_db_connection():
    try:
        connection = get_db_connection()
        connection.close()  # Cierra la conexión
        return jsonify({"status": "success", "message": "Database connection successful"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "Database connection failed", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)