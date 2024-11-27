import psycopg2
from flask import Flask, jsonify

app = Flask(__name__)

# Configuración de conexión
def get_db_connection():
    #database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/railway"
    database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/goshort"
    connection = psycopg2.connect(database_url)
    return connection

@app.route('/user/<string:user_id>', methods=['GET'])
def get_user_info(user_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Consulta para obtener la información del usuario
        cursor.execute('''
            SELECT u.apple_id, u.subscription_type_id, array_agg(url.name_url) AS urls_created
            FROM goshort.pro.users u
            LEFT JOIN goshort.pro.url url 
            ON u.user_id = url.user_id
            WHERE u.user_id = %s
            GROUP BY u.user_id;
        ''', (user_id,))
        
        user_data = cursor.fetchone()

        # Verificar si el usuario existe
        if user_data is None:
            return jsonify({"message": "User  not found"}), 404

        # Crear un diccionario para la respuesta JSON
        user_info = {
            "email": user_data[0],
            "subscription_status": user_data[1],
            "urls_created": user_data[2] if user_data[2] is not None else []
        }

        return jsonify(user_info), 200

    except Exception as e:
        print(f"Error al obtener la información del usuario: {e}")
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        # Asegúrate de cerrar el cursor y la conexión si fueron creados
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)