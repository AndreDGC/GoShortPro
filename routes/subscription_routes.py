from flask import Blueprint, request, jsonify
from db import get_db_connection
from datetime import datetime, timedelta

subscription_routes = Blueprint('subscription_routes', __name__)

@subscription_routes.route('/user/<string:user_id>/upgrade', methods=['POST'])
def upgrade_subscription(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        data = request.json
        subscription_type_id = data.get('subscription_type_id')

        if subscription_type_id not in [0, 1, 2, 3]:
            return jsonify({
                "status": "error",
                "code": 400,
                "message": "Invalid request. Please check the data entered.",
                "data": None
            }), 400

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
                "message": f"Subscription for user not found, id: {user_id}",
                "data": None
            }), 404

        cursor.execute('''
            UPDATE goshort.pro.users 
            SET subscription_type_id = %s 
            WHERE user_id = %s;
        ''', (subscription_type_id, user_id))

        connection.commit()

        return jsonify({
            "status": "success",
            "code": 200,
            "message": f"User  upgraded to {subscription_desc} successfully",
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
        print(f"Error updating user subscription: {e}")
        return jsonify({"status": "error", "code": 500, "message": "Server error", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()