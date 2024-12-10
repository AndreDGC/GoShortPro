import bcrypt
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime, timedelta

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
    password = data.get('password')
    subscription_type_id = data.get('subscription_type_id', 0)  # Valor predeterminado es 0 (free)
    user_count = data.get('user_count', 1)  # Opcional: valor por defecto

    # Verifica que los datos necesarios estén presentes
    if not name or not apple_id or not password:
        return jsonify({
            "status": "error",
            "code": 400,
            "message": "Solicitud inválida. Verifique los datos ingresados.",
            "data": {
                "faltan_datos": ["name", "apple_id", "password"]
            }
        }), 400

    # Hash de la contraseña
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Ejecuta el INSERT
        cursor.execute('''
            INSERT INTO goshort.pro.users (name, apple_id, password, subscription_type_id)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, apple_id, name;
        ''', (name, apple_id, hashed_password, subscription_type_id))
        
        # Obtén el ID del nuevo usuario insertado
        new_user_id, new_apple_id, new_name = cursor.fetchone()

        # Confirma la transacción
        connection.commit()

        # Response ajustado al requerimiento
        response_post_user = {
            "status": "success",
            "code": 201,
            "message": "Usuario creado exitosamente",
            "data": {
                "user_id": new_user_id,
                "apple_id": new_apple_id,
                "name": new_name,
            }
        }
        return jsonify(response_post_user), 201

    except Exception as e:
        print(f"Error al crear el usuario: {e}")
        if connection:
            connection.rollback()  # Revierte en caso de error

        # Manejo específico para errores de clave duplicada
        if "duplicate key value violates unique constraint" in str(e):
            return jsonify({
                "status": "error",
                "code": 409,
                "message": "El correo ya ha sido registrado."
            }), 409
                        
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
        SELECT 
            u.user_id, 
            u.apple_id, 
            u.name, 
            cst.desc_subscription_type AS type,
            COALESCE(json_agg(json_build_object(
                'url_id', url.url_id,
                'destination', url.base_url,
                'creation_date', url.creation_date::TEXT
            )) FILTER (WHERE url.url_id IS NOT NULL), '[]'::json) AS urls
        FROM goshort.pro.users u
        LEFT JOIN goshort.pro.url url 
            ON u.user_id = url.user_id
        LEFT JOIN goshort.pro.cat_subscription_type cst
            ON u.subscription_type_id = cst.subscription_type_id
        WHERE u.user_id = %s
        GROUP BY u.user_id, cst.desc_subscription_type;
        ''', (user_id,))
        
        user_data = cursor.fetchone()

        # Verificar si el usuario existe
        if user_data is None:
            return jsonify({"message": "User  not found"}), 404

        # Crear un diccionario para la respuesta JSON
        respose_get_user = {
            "status": "success",
            "code": 201,
            "message": "Usuario consultado exitosamente",
            "data": {
                "user_id": user_data[0],
                "email": user_data[1],
                "name": user_data[2],
                "type": user_data[3],
                "urls": user_data[4],
                #"subscription": None
                #"urls:" urls if urls else [], #"urls_created": user_data[2] if user_data[2] is not None else []    
                #"subscription_status": user_data[1]
            },
        }
        return jsonify(respose_get_user), 200

    except Exception as e:
        print(f"Error al obtener la información del usuario: {e}")
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        # Asegúrate de cerrar el cursor y la conexión si fueron creados
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

### 
# EP LOGIN
# Endpoint para iniciar sesión
@app.route('/user/login', methods=['POST'])
def login_user():
    # Obtener los datos del cuerpo de la solicitud
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email y contraseña son requeridos"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Consulta para obtener el usuario por email
        cursor.execute('''
        SELECT user_id, password, name, subscription_type_id
        FROM goshort.pro.users
        WHERE apple_id = %s  -- Cambia esto si el email no es el apple_id
        ''', (email,))
        
        user_data = cursor.fetchone()

        # Verificar si el usuario existe
        if user_data is None:
            return jsonify({"message": "Credenciales inválidas"}), 401

        user_id, password_hash, name, subscription_type_id = user_data

        # Verificar la contraseña
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return jsonify({"message": "Credenciales inválidas"}), 401

        # Crear un diccionario para la respuesta JSON
        response_login = {
            "status": "success",
            "code": 200,
            "message": "Inicio de sesión exitoso",
            "data": {
                "user_id": user_id,
                "email": email,
                "name": name,
                "subscription_type_id": subscription_type_id,
            },
        }
        return jsonify(response_login), 200

    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        return jsonify({"message": "Error del servidor", "error": str(e)}), 500

    finally:
        # Asegúrate de cerrar el cursor y la conexión si fueron creados
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

###


# POST URL (Deprecado, ahora se postea por RANDOM)
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
            RETURNING url_id, base_url, creation_date, short_url;
        ''', (name_url, base_url, user_id))
        
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

@app.route('/user/<string:user_id>/urls/<string:url_id>', methods=['GET'])
def get_user_url(user_id, url_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Consulta para obtener la URL asociada al usuario y al ID de la URL
        cursor.execute('''
            SELECT 
            url.base_url
            FROM goshort.pro.url url
            LEFT JOIN goshort.pro.users users
            ON users.user_id = url.user_id
            WHERE url.user_id = %s
            AND url.url_id = %s;
        ''', (user_id, url_id))
        
        url = cursor.fetchone()

        # Verificar si se encontró la URL
        if not url:
            return jsonify({
                "status": "error",
                "code": 404,
                "message": "URL no encontrada para este usuario",
                "data": None
            }), 404

        # Registrar visita en la tabla de analytics
        cursor.execute('''
            INSERT INTO goshort.pro.analytics (url_id, visit_count, last_visit)
            VALUES (%s, 1, NOW())
            ON CONFLICT (url_id) 
            DO UPDATE SET 
                visit_count = goshort.pro.analytics.visit_count + 1,
                last_visit = NOW();
        ''', (url_id,))

        # Confirmar los cambios en la base de datos
        connection.commit()

        # Si se encuentra la URL, devolver la respuesta esperada
        return jsonify({
            "status": "success",
            "code": 302,
            "message": "Redireccionando a la URL original",
            "data": {
                "destination": url[0]  # Suponiendo que url[0] contiene la URL original
            }
        }), 302

    except Exception as e:
        print(f"Error al obtener la URL del usuario: {e}")
        return jsonify({"status": "error", "code": 500, "message": "Error del servidor", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

# POST SUBSCRIPTIONS
@app.route('/user/<string:user_id>/upgrade', methods=['POST'])
def upgrade_subscription(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Obtener el tipo de suscripción del cuerpo de la solicitud
        data = request.json
        subscription_type_id = data.get('subscription_type_id')

        # Validar el tipo de suscripción
        if subscription_type_id not in [0, 1, 2, 3]:
            return jsonify({
                "status": "error",
                "code": 400,
                "message": "Solicitud invalida. Verifique los datos ingresados.",
                "data": None
            }), 400

        # Definir la duración y calcular la fecha de finalización
        if subscription_type_id == 1:  # mensual
            duration = "1 month"
            end_date = datetime.now() + timedelta(days=30)
            subscription_desc = "mensual"
        elif subscription_type_id == 2:  # trimestral
            duration = "3 months"
            end_date = datetime.now() + timedelta(days=90)
            subscription_desc = "trimestral"
        elif subscription_type_id == 3:  # anual
            duration = "12 months"
            end_date = datetime.now() + timedelta(days=365)
            subscription_desc = "anual"
        else:  # free
            duration = "indefinido"
            end_date = None  # Puede ser indefinido
            subscription_desc = "free"

        start_date = datetime.now()

        # Actualizar la suscripción existente
        cursor.execute('''
            INSERT INTO goshort.pro.subscriptions (user_id, subscription_type_id, start_date, end_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE 
            SET subscription_type_id = EXCLUDED.subscription_type_id, 
                start_date = EXCLUDED.start_date, 
                end_date = EXCLUDED.end_date
            RETURNING subscription_id;
        ''', (user_id, subscription_type_id, start_date, end_date))

        subscription_id = cursor.fetchone()

        if subscription_id is None:
            return jsonify({
                "status": "error",
                "code": 404,
                "message": f"No se encontro la suscripcion del usuario con id: {user_id}",
                "data": None
            }), 404

        # Actualizar el campo subscription_type_id en la tabla users
        cursor.execute('''
            UPDATE goshort.pro.users 
            SET subscription_type_id = %s 
            WHERE user_id = %s;
        ''', (subscription_type_id, user_id))

        # Confirma la transacción
        connection.commit()

        # Si la actualización es exitosa, devolver la respuesta esperada
        return jsonify({
            "status": "success",
            "code": 200,
            "message": f"Usuario actualizado a {subscription_desc} exitosamente",
            "data": {
                "user_id": user_id,
                "subscription_type_id": subscription_type_id,
                "subscription": {
                    "subscription_id": subscription_id[0],
                    "duration": duration,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d') if end_date else None
                }
            }
        }), 200

    except Exception as e:
        print(f"Error al actualizar la suscripcion del usuario: {e}")
        return jsonify({"status": "error", "code": 500, "message": "Error del servidor", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

# GET ANALYTICS
@app.route('/user/<string:user_id>/urls/<string:url_id>/analytics', methods=['GET'])
def get_url_analytics(user_id, url_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Consulta para obtener la información de la URL y sus analíticas
        cursor.execute('''
            SELECT 
                a.url_id,
                u.name_url,
                u.base_url,
                u.short_url,
                u.creation_date,
                a.visit_count,
                u.user_id
            FROM goshort.pro.analytics a
            JOIN goshort.pro.url u ON a.url_id = u.url_id
            WHERE u.user_id = %s AND a.url_id = %s;
        ''', (user_id, url_id))
        
        analytics_data = cursor.fetchone()

        # Verificar si se encontró la URL y sus analíticas
        if not analytics_data:
            return jsonify({
                "status": "error",
                "code": 404,
                "message": "Analiticas no encontradas para esta URL",
                "data": None
            }), 404

        # Construir la respuesta
        response_data = {
            "url_id": analytics_data[0],
            "short_url": analytics_data[3],  # short_url
            "destination": analytics_data[2],  # base_url
            "creation_date": analytics_data[4].isoformat() if analytics_data[4] else None,  # creation_date
            "visits": analytics_data[5],  # visit_count
            "analytics": {
                "count": analytics_data[5],  # visit_count
                "user_id": analytics_data[6]  # user_id
            }
        }

        return jsonify({
            "status": "success",
            "code": 200,
            "message": "Analiticas de URL obtenidas exitosamente",
            "data": response_data
        }), 200

    except Exception as e:
        print(f"Error al obtener las analiticas de la URL: {e}")
        return jsonify({"status": "error", "code": 500, "message": "Error del servidor", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(debug=True)