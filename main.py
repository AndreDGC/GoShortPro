import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuración de conexión
def get_db_connection():
    #database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/railway"
    database_url = "postgresql://postgres:IgtzJLbHpqJPoimAEYCVTqkDtQFFPqEz@autorack.proxy.rlwy.net:39767/goshort"
    connection = psycopg2.connect(database_url)
    return connection

# POST USER
@app.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()  # Obtén los datos JSON de la solicitud
    
    # Extrae los valores del JSON
    name = data.get('name')
    apple_id = data.get('apple_id')
    subscription_type_id = data.get('subscription_type_id')
    user_count = data.get('user_count', 1)  # Opcional: valor por defecto

    # Verifica que los datos necesarios estén presentes
    if not name or not apple_id or subscription_type_id is None:
        return jsonify({"message": "Faltan datos obligatorios"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Ejecuta el INSERT
        cursor.execute('''
            INSERT INTO goshort.pro.users (name, apple_id, subscription_type_id, user_count)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id;
        ''', (name, apple_id, subscription_type_id, user_count))
        
        # Obtén el ID del nuevo usuario insertado
        new_user_id = cursor.fetchone()[0]

        # Confirma la transacción
        connection.commit()

        return jsonify({"message": "Usuario creado exitosamente", "user_id": new_user_id}), 201

    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        if connection:
            connection.rollback()  # Revierte en caso de error
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


# GET USER
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

# POST URL
@app.route('/urls', methods=['POST'])
def create_url():
    data = request.get_json()  # Obtén los datos JSON de la solicitud
    
    # Extrae los valores del JSON
    name_url = data.get('name_url')
    destination = data.get('destination')
    user_id = data.get('user_id')

    # Verifica que los datos necesarios estén presentes
    if not name_url or not destination or user_id is None:
        return jsonify({"message": "Faltan datos obligatorios"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Ejecuta el INSERT
        cursor.execute('''
            INSERT INTO goshort.pro.url (name_url, destination, user_id)
            VALUES (%s, %s, %s)
            RETURNING url_id;
        ''', (name_url, destination, user_id))
        
        # Obtén el ID de la nueva URL insertada
        new_url_id = cursor.fetchone()[0]

        # Confirma la transacción
        connection.commit()

        return jsonify({"message": "URL creada exitosamente", "url_id": new_url_id}), 201

    except Exception as e:
        print(f"Error al crear la URL: {e}")
        if connection:
            connection.rollback()  # Revierte en caso de error
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

# GET URL
@app.route('/user/<string:user_id>/urls', methods=['GET'])
def get_user_urls(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Consulta para obtener las URLs asociadas al usuario
        cursor.execute('''
            SELECT url.name_url
            FROM goshort.pro.url url
            WHERE url.user_id = %s;
        ''', (user_id,))
        
        urls = cursor.fetchall()

        # Verificar si el usuario tiene URLs
        if not urls:
            return jsonify({"message": "No URLs found for this user"}), 404

        # Convertir los resultados en una lista de diccionarios
        urls_list = [{"name_url": url[0]} for url in urls]

        return jsonify(urls_list), 200

    except Exception as e:
        print(f"Error al obtener las URLs del usuario: {e}")
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()            

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)