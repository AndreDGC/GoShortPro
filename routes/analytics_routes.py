from flask import Blueprint, jsonify
from db import get_db_connection

analytics_routes = Blueprint('analytics_routes', __name__)

@analytics_routes.route('/user/<string:user_id>/urls/<string:url_id>/analytics', methods=['GET'])
def get_url_analytics(user_id, url_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
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

        if not analytics_data:
            return jsonify({
                "status": "error",
                "code": 404,
                "message": "Analytics not found for this URL",
                "data": None
            }), 404

        response_data = {
            "url_id": analytics_data[0],
            "short_url": analytics_data[3],
            "destination": analytics_data[2],
            "creation_date": analytics_data[4].isoformat() if analytics_data[4] else None,
            "visits": analytics_data[5],
            "analytics": {
                "count": analytics_data[5],
                "user_id": analytics_data[6]
            }
        }

        return jsonify({
            "status": "success",
            "code": 200,
            "message": "URL analytics successfully obtained",
            "data": response_data
        }), 200

    except Exception as e:
        print(f"Error getting analytics from URL: {e}")
        return jsonify({"status": "error", "code": 500, "message": "Server error", "error": str(e)}), 500

    finally:
        cursor.close()
        connection.close()