"""
نموذج الذكاء الاصطناعي لتقييم مخاطر دعامة القلب
Binary Classification: Normal / Early Blockage
"""

import os
import pickle
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# المسار إلى ملف البيانات
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'sample_sensor_data.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'risk_model.pkl')
SCALER_PATH = os.path.join(BASE_DIR, 'models', 'scaler.pkl')

# عتبة الخطر للتنبيهات (نسبة مئوية)
WARNING_THRESHOLD = 40
CRITICAL_THRESHOLD = 70


def load_and_train_model():
    """تحميل البيانات وتدريب النموذج وحفظه"""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"ملف البيانات غير موجود: {DATA_PATH}")
    
    df = pd.read_csv(DATA_PATH)
    X = df[['flow_rate', 'p1', 'p2', 'delta_p']]
    y = df['label'].map({'normal': 0, 'early_blockage': 1})
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # حفظ النموذج والمقياس
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
    
    return model, scaler


def get_model():
    """تحميل النموذج المحفوظ أو تدريب نموذج جديد"""
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        return model, scaler
    return load_and_train_model()


def predict_risk(flow_rate, p1, p2, delta_p):
    """
    توقع نسبة الخطر والحالة
    المدخلات: flow_rate (mL/min), p1 (mmHg), p2 (mmHg), delta_p (mmHg)
    المخرجات: risk_score (%), prediction_label, status
    """
    model, scaler = get_model()
    
    features = pd.DataFrame([[flow_rate, p1, p2, delta_p]],
                           columns=['flow_rate', 'p1', 'p2', 'delta_p'])
    features_scaled = scaler.transform(features)
    
    prediction = model.predict(features_scaled)[0]
    proba = model.predict_proba(features_scaled)[0]
    
    # نسبة الخطر = احتمال Early Blockage * 100
    risk_score = float(proba[1] * 100)
    
    prediction_label = 'early_blockage' if prediction == 1 else 'normal'
    
    if risk_score < WARNING_THRESHOLD:
        status = 'normal'
    elif risk_score < CRITICAL_THRESHOLD:
        status = 'warning'
    else:
        status = 'critical'
    
    return {
        'risk_score': round(risk_score, 1),
        'prediction_label': prediction_label,
        'status': status,
        'should_alert': risk_score >= WARNING_THRESHOLD
    }


def get_status_description(status):
    """شرح نصي قصير للحالة"""
    descriptions = {
        'normal': 'الأداء طبيعي. الدعامة تعمل بشكل سليم.',
        'warning': 'تحذير: احتمالية بداية انسداد. يوصى بالمتابعة.',
        'critical': 'خطر: مؤشرات انسداد واضحة. إجراء فحص طبي فوري.'
    }
    return descriptions.get(status, 'غير معروف')
