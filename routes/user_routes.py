from flask import Blueprint, request, jsonify
from db import get_db_connection
import bcrypt
import base64

user_routes = Blueprint('user_routes', __name__)

@user_routes.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()
    name = data.get('name')
    apple_id = data.get('apple_id')
    password = data.get('password')
    subscription_type_id = data.get('subscription_type_id', 0)

    if not name or not apple_id or not password:
        return jsonify({
            "status": "error",
            "code": 400,
            "message": "Invalid request. Please check the data entered.",
            "data": {
                "missing_data": [field for field in ['name', 'apple_id', 'password'] if not locals()[field]]
            }
        }), 400

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

        return jsonify({
            "status": "success",
            "code": 201,
            "message": "User  created successfully",
            "data": {
                "user_id": new_user_id,
                "apple_id": new_apple_id,
                "name": new_name,
            }
        }), 201

    except Exception as e:
        print(f"Error creating user: {e}")
        if connection:
            connection.rollback()

        if "duplicate key value violates unique constraint" in str(e):
            return jsonify({
                "status": "error",
                "code": 409,
                "message": "The email has already been registered.",
                "data": None
            }), 409

        return jsonify({
            "status": "error",
            "code": 500,
            "message": "Server error",
            "data": str(e)
        }), 500

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
        return jsonify({
            "status": "error",
            "code": 400,
            "message": "Email and password are required",
            "data": None
        }), 400

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
            return jsonify({
                "status": "error",
                "code": 401,
                "message": "Invalid credentials",
                "data": None
            }), 401

        user_id, password_hash_base64, name, subscription_type_id = user_data
        password_hash = base64.b64decode(password_hash_base64)

        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            return jsonify({
                "status": "error",
                "code": 401,
                "message": "Invalid credentials",
                "data": None
            }), 401

        return jsonify({
            "status": "success",
            "code": 200,
            "message": " Login successful",
            "data": {
                "user_id": user_id,
                "email": email,
                "name": name,
                "subscription_type_id": subscription_type_id,
            },
        }), 200

    except Exception as e:
        print(f"Error logging in: {e}")
        return jsonify({
            "status": "error",
            "code": 500,
            "message": "Server error",
            "data": str(e)
        }), 500

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
            return jsonify({
                "status": "error",
                "code": 404,
                "message": "User  not found",
                "data": None
            }), 404

        response_get_user = {
            "status": "success",
            "code": 200,
            "message": "User successfully consulted",
            "data": {
                "user_id": user_data[0],
                "apple_id": user_data[1],
                "name": user_data[2],
                "type": user_data[3],
                "urls": user_data[4],
            },
        }
        return jsonify(response_get_user), 200

    except Exception as e:
        print(f"Error getting user information: {e}")
        return jsonify({
            "status": "error",
            "code": 500,
            "message": "Server error",
            "data": str(e)
        }), 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
