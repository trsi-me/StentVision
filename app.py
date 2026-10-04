"""
StentVision - نظام مراقبة أداء دعامة القلب
Backend: Flask + SQLite
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from models.risk_model import predict_risk, get_status_description, load_and_train_model

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')


def get_db():
    """الاتصال بقاعدة البيانات"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """تهيئة جداول قاعدة البيانات"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_rate REAL,
            p1 REAL,
            p2 REAL,
            delta_p REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER,
            risk_score REAL,
            prediction_label TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reading_id) REFERENCES sensor_readings(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reading_id INTEGER,
            severity TEXT,
            description TEXT,
            action TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reading_id) REFERENCES sensor_readings(id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_reading_and_prediction(flow_rate, p1, p2, delta_p):
    """حفظ القراءة والتنبؤ والتنبيهات"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO sensor_readings (flow_rate, p1, p2, delta_p) VALUES (?, ?, ?, ?)',
        (flow_rate, p1, p2, delta_p)
    )
    reading_id = cursor.lastrowid
    
    result = predict_risk(flow_rate, p1, p2, delta_p)
    
    cursor.execute(
        'INSERT INTO predictions (reading_id, risk_score, prediction_label, status) VALUES (?, ?, ?, ?)',
        (reading_id, result['risk_score'], result['prediction_label'], result['status'])
    )
    
    if result['should_alert']:
        severity = 'high' if result['status'] == 'critical' else ('medium' if result['status'] == 'warning' else 'low')
        
        desc = get_status_description(result['status'])
        action = 'متابعة طبية' if result['status'] in ['warning', 'critical'] else 'مراقبة'
        
        cursor.execute(
            'INSERT INTO alerts (reading_id, severity, description, action) VALUES (?, ?, ?, ?)',
            (reading_id, severity, desc, action)
        )
    
    conn.commit()
    conn.close()
    
    return result


@app.route('/')
def index():
    """الصفحة الرئيسية - لوحة التحكم"""
    return render_template('dashboard.html')


@app.route('/history')
def history():
    """صفحة السجل"""
    return render_template('history.html')


@app.route('/alerts')
def alerts_page():
    """صفحة التنبيهات"""
    return render_template('alerts.html')


@app.route('/settings')
def settings():
    """صفحة الإعدادات"""
    return render_template('settings.html')


# --- واجهات برمجة التطبيقات (API) ---

@app.route('/api/reading', methods=['POST'])
def api_receive_reading():
    """
    استقبال قراءة من المستشعرات (جاهز للربط مع Arduino/ESP32)
    يتوقع JSON: { flow_rate, p1, p2, delta_p }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'بيانات غير صالحة'}), 400
    
    try:
        flow_rate = float(data.get('flow_rate', 0))
        p1 = float(data.get('p1', 0))
        p2 = float(data.get('p2', 0))
        delta_p = float(data.get('delta_p', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'قيم غير صالحة'}), 400
    
    result = save_reading_and_prediction(flow_rate, p1, p2, delta_p)
    result['description'] = get_status_description(result['status'])
    
    return jsonify(result)


@app.route('/api/reading/simulate', methods=['POST'])
def api_simulate_reading():
    """محاكاة قراءة للاختبار"""
    data = request.get_json() or {}
    flow_rate = float(data.get('flow_rate', 85))
    p1 = float(data.get('p1', 120))
    p2 = float(data.get('p2', 95))
    delta_p = float(data.get('delta_p', 25))
    
    result = save_reading_and_prediction(flow_rate, p1, p2, delta_p)
    result['description'] = get_status_description(result['status'])
    
    return jsonify(result)


@app.route('/api/readings')
def api_readings():
    """جميع القراءات (للسجل)"""
    limit = request.args.get('limit', 100, type=int)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM sensor_readings ORDER BY id DESC LIMIT ?', (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route('/api/readings/latest')
def api_latest_readings():
    """آخر 4 قراءات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM sensor_readings ORDER BY id DESC LIMIT 4'
    )
    rows = cursor.fetchall()
    conn.close()
    
    readings = [dict(row) for row in reversed(rows)]
    return jsonify(readings)


@app.route('/api/chart/flow')
def api_chart_flow():
    """بيانات رسم تدفق الدم"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT flow_rate, created_at FROM sensor_readings ORDER BY id DESC LIMIT 50'
    )
    rows = cursor.fetchall()
    conn.close()
    
    data = [{'value': row['flow_rate'], 'time': row['created_at']} for row in reversed(rows)]
    return jsonify(data)


@app.route('/api/chart/pressure')
def api_chart_pressure():
    """بيانات رسم فرق الضغط"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT delta_p, created_at FROM sensor_readings ORDER BY id DESC LIMIT 50'
    )
    rows = cursor.fetchall()
    conn.close()
    
    data = [{'value': row['delta_p'], 'time': row['created_at']} for row in reversed(rows)]
    return jsonify(data)


@app.route('/api/chart/risk')
def api_chart_risk():
    """بيانات رسم نسبة الخطر"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.risk_score, p.created_at 
        FROM predictions p 
        ORDER BY p.id DESC LIMIT 50
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    data = [{'value': row['risk_score'], 'time': row['created_at']} for row in reversed(rows)]
    return jsonify(data)


@app.route('/api/risk/current')
def api_current_risk():
    """آخر تقييم للخطر"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.risk_score, p.prediction_label, p.status 
        FROM predictions p 
        ORDER BY p.id DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        result = dict(row)
        result['description'] = get_status_description(result['status'])
        return jsonify(result)
    
    return jsonify({
        'risk_score': 0,
        'prediction_label': 'normal',
        'status': 'normal',
        'description': 'لا توجد قراءات حتى الآن.'
    })


@app.route('/api/alerts')
def api_alerts():
    """قائمة التنبيهات"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM alerts ORDER BY id DESC LIMIT 20'
    )
    rows = cursor.fetchall()
    conn.close()
    
    alerts = [dict(row) for row in rows]
    return jsonify(alerts)


@app.route('/api/train', methods=['POST'])
def api_train_model():
    """إعادة تدريب النموذج"""
    try:
        load_and_train_model()
        return jsonify({'success': True, 'message': 'تم تدريب النموذج بنجاح'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    load_and_train_model()
    app.run(debug=True, host='0.0.0.0', port=5000)
