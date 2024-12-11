from flask import Blueprint, request, jsonify
from db import get_db_connection
import bcrypt
import base64

user_routes = Blueprint('user_routes', __name__)

def create_response(code, status, message, data=None):
    return jsonify({
        "code": code,
        "status": status,
        "message": message,
        "data": data if data else {}
    }), code

@user_routes.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name')
    apple_id = data.get('apple_id')
    password = data.get('password')
    subscription_type_id = data.get('subscription_type_id', 0)

    if not name or not apple_id or not password:
        missing_data = [field for field in ["name", "apple_id", "password"] if not data.get(field)]
        return create_response(400, "error", "Invalid request. Please check the data entered.", {"missing_data": missing_data})

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    hashed_password_base64 = base64.b64encode(hashed_password).decode('utf-8')

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute('''
            INSERT INTO goshort.pro.users (name, apple_id, password, subscription_type_id)
            VALUES (%s, %s, %s, %s)
            RETURNING user_id, apple_id, name;
        ''', (name, apple_id, hashed_password_base64, subscription_type_id))

        new_user_id, new_apple_id, new_name = cursor.fetchone()
        connection.commit()

        return create_response(201, "success", "User created successfully", {
            "user_id": new_user_id,
            "apple_id": new_apple_id,
            "name": new_name
        })

    except Exception as e:
        print(f"Error creating user: {e}")
        if connection:
            connection.rollback()

        if "duplicate key value violates unique constraint" in str(e):
            return create_response(409, "error", "The email has already been registered.")

        return create_response(500, "error", "Server error", {"error": str(e)})

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

@user_routes.route('/user/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return create_response(400, "error", "Email and password are required")

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute('''
        SELECT user_id, password, name, subscription_type_id
        FROM goshort.pro.users
        WHERE apple_id = %s
        ''', (email,))

        user_data = cursor.fetchone()

        if user_data is None:
            return create_response(401, "error", "Invalid credentials")

        user_id, password_hash_base64, name, subscription_type_id = user_data
        password_hash = base64.b64decode(password_hash_base64)

        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            return create_response(401, "error", "Invalid credentials")

        return create_response(200, "success", "Login successful", {
            "user_id": user_id,
            "email": email,
            "name": name,
            "subscription_type_id": subscription_type_id
        })

    except Exception as e:
        print(f"Error logging in: {e}")
        return create_response(500, "error", "Server error", {"error": str(e)})

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

@user_routes.route('/user/<string:user_id>', methods=['GET'])
def get_user_info(user_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

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

        if user_data is None:
            return create_response(404, "error", "User not found")

        return create_response(200, "success", "User successfully consulted", {
            "user_id": user_data[0],
            "apple_id": user_data[1],
            "name": user_data[2],
            "type": user_data[3],
            "urls": user_data[4]
        })

    except Exception as e:
        print(f"Error getting user information: {e}")
        return create_response(500, "error", "Server error", {"error": str(e)})

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
