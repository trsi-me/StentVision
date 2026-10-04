# StentVision

## 1 ما هو المشروع

StentVision تطبيق ويب محلي لمراقبة أداء دعامة قلب بعد زراعتها. يستقبل أربع قراءات: تدفق الدم `flow_rate`، الضغط قبل الدعامة `p1`، الضغط بعد الدعامة `p2`، وفرق الضغط `delta_p`. يحفظ القراءة في SQLite، ويشغّل مصنفاً ثنائياً (طبيعي / بداية انسداد)، ويعرض لوحة ورسوماً وتنبيهات.

التعليق في أعلى `app.py`: «نظام مراقبة أداء دعامة القلب». التطبيق الحالي برمجي. مسار `POST /api/reading` مهيأ لاستقبال JSON من جهاز خارجي، ولا يوجد في المجلد كود Arduino أو ESP32.

## 2 لمن هذا المشروع

| الجهة | ما يظهر في الكود |
| --- | --- |
| مشغّل اللوحة | يفتح الصفحات `/` و`/history` و`/alerts` و`/settings` |
| جهاز إرسال قراءات | يرسل JSON إلى `POST /api/reading` |
| مطور | يعدّل `app.py` و`models/risk_model.py` وملفات `templates` و`static` |

حسابات مستخدمين وأدوار: غير موجود في الملفات الحالية.

## 3 الميزات الفعلية

| الميزة | أين |
| --- | --- |
| لوحة رئيسية | `GET /` يعرض `templates/dashboard.html` |
| سجل القراءات | `GET /history` |
| صفحة التنبيهات | `GET /alerts` |
| صفحة الإعدادات | `GET /settings` |
| حفظ قراءة حقيقية | `POST /api/reading` |
| محاكاة قراءة بقيم افتراضية | `POST /api/reading/simulate` (افتراضياً flow 85 وp1 120 وp2 95 وdelta_p 25) |
| رسوم التدفق والضغط والخطر | `/api/chart/flow` و`/api/chart/pressure` و`/api/chart/risk` (آخر 50 نقطة) |
| آخر تقييم خطر | `GET /api/risk/current` |
| آخر 20 تنبيهاً | `GET /api/alerts` |
| إعادة تدريب النموذج | `POST /api/train` |
| تصنيف RandomForest | `models/risk_model.py` |
| عتبات الحالة | أقل من 40 طبيعي، من 40 وأقل من 70 تحذير، من 70 فأعلى حرج |

التنبيه يُكتب عندما `risk_score >= 40`. النص العربي للحالات في `get_status_description`.

## 4 أمثلة واقعية

إرسال قراءة:

```json
{
  "flow_rate": 85.5,
  "p1": 120.0,
  "p2": 95.0,
  "delta_p": 25.0
}
```

| الحقل | الوحدة المذكورة في دالة التنبؤ | المعنى في الكود |
| --- | --- | --- |
| flow_rate | mL/min | تدفق |
| p1 | mmHg | ضغط قبل الدعامة |
| p2 | mmHg | ضغط بعد الدعامة |
| delta_p | mmHg | فرق الضغط |

ملف التدريب `data/sample_sensor_data.csv` أعمدته: `flow_rate,p1,p2,delta_p,label`. قيم التصنيف في التدريب: `normal` و`early_blockage`.

رد التنبؤ يحتوي `risk_score` و`prediction_label` و`status` و`should_alert`، وتضيف المسارات حقل `description`.

## 5 رحلة الاستخدام

1. تشغيل `python app.py` ينشئ الجداول إن غابت، ثم يدرب النموذج من ملف CSV ويحفظ `models/risk_model.pkl` و`models/scaler.pkl`.
2. المتصفح يفتح `http://127.0.0.1:5000` لأن `app.run` يضبط المنفذ 5000.
3. الواجهة تطلب آخر القراءات والرسوم والخطر والتنبيهات.
4. إرسال JSON إلى `/api/reading` أو ضغط المحاكاة يحفظ صفاً في `sensor_readings` وصفاً في `predictions`، وصفاً في `alerts` عند تجاوز العتبة.
5. صفحة السجل تقرأ `/api/readings` بحد افتراضي 100.

## 6 الوحدات البرمجية

| الملف | الدور |
| --- | --- |
| `app.py` | Flask، SQLite، المسارات |
| `models/risk_model.py` | التدريب والتنبؤ ووصف الحالة |
| `models/__init__.py` | حزمة النماذج |
| `data/sample_sensor_data.csv` | بيانات التدريب |
| `templates/*.html` | الصفحات |
| `static/css/style.css` و`static/js/main.js` | الشكل والسلوك في المتصفح |
| `requirements.txt` | إصدارات المكتبات |

## 7 الكيانات

| الكيان | الجدول | الحقول |
| --- | --- | --- |
| قراءة حساس | `sensor_readings` | `id`, `flow_rate`, `p1`, `p2`, `delta_p`, `created_at` |
| تنبؤ | `predictions` | `id`, `reading_id`, `risk_score`, `prediction_label`, `status`, `created_at` |
| تنبيه | `alerts` | `id`, `reading_id`, `severity`, `description`, `action`, `created_at` |

`reading_id` مفتاح أجنبي إلى `sensor_readings(id)`.

شدة التنبيه في الكود: `high` للحالة `critical`، و`medium` للحالة `warning`. فرع `low` موجود في التعبير الشرطي، ومسار التنبيه لا يُستدعى إلا عند `should_alert` أي درجة 40 أو أكثر، فالحالتان المخزنتان فعلياً هما `medium` و`high`.

حقل `action`: النص «متابعة طبية» للحالات `warning` و`critical`، والنص «مراقبة» لغيرهما داخل نفس الكتلة.

## 8 الصلاحيات

غير موجود في الملفات الحالية. كل المسارات مفتوحة بدون تسجيل دخول.

## 9 الأتمتة

| السلوك | التفاصيل |
| --- | --- |
| إنشاء الجداول | `init_db()` عند تشغيل `python app.py` |
| تدريب عند الإقلاع | `load_and_train_model()` تُستدعى دائماً من كتلة `__main__` حتى لو وُجد ملف النموذج |
| تدريب عند الطلب | `POST /api/train` |
| تقسيم التدريب | `train_test_split` بنسبة اختبار 0.2 و`random_state=42` |
| النموذج | `RandomForestClassifier(n_estimators=100, random_state=42)` بعد `StandardScaler` |

لا توجد مهام مجدولة (cron) في الملفات الحالية.

## 10 التكامل

المسار `POST /api/reading` يتوقع JSON بالحقول الأربعة. تعليق الدالة يذكر جاهزية الربط مع Arduino أو ESP32. لا يوجد ملف جهاز داخل المشروع.

ملف README السابق تضمّن مثالاً توضيحياً بلغة C++ لإرسال HTTP. هذا المثال غير موجود كملف مصدر في المجلد الحالي، والعقد الفعلي هو مسار Flask أعلاه.

## 11 المصطلحات

| المصطلح | المعنى هنا |
| --- | --- |
| Flow Rate | عمود `flow_rate` |
| P1 / P2 | الضغطان قبل الدعامة وبعدها |
| Delta P | عمود `delta_p` |
| risk_score | احتمال صنف بداية الانسداد مضروباً في 100، مقرباً لخانة واحدة |
| early_blockage | تسمية الصف في CSV عندما يكون الصنف 1 |
| status | `normal` أو `warning` أو `critical` |

## 12 الأسئلة الشائعة

| السؤال | الجواب من الملفات |
| --- | --- |
| أين تُحفظ البيانات؟ | ملف `database.db` بجانب `app.py` |
| هل يعيد التشغيل التدريب؟ | نعم عند `python app.py`، لأن `load_and_train_model` تُستدعى قبل `app.run` |
| ماذا لو غاب ملف CSV؟ | `load_and_train_model` ترفع `FileNotFoundError` |
| هل توجد مصادقة؟ | غير موجود في الملفات الحالية |
| ما المنفذ؟ | 5000، والمضيف `0.0.0.0`، و`debug=True` |

## 13 البنية المعمارية

```
المتصفح
   |  HTML من templates
   v
Flask app.py :5000
   |                \
   |                 +--> models/risk_model.py
   |                      CSV + RandomForest + Scaler
   v
SQLite database.db
   sensor_readings
   predictions
   alerts
```

جهاز خارجي، إن وُصل لاحقاً، يرسل POST إلى `/api/reading` ثم يسلك نفس مسار الحفظ والتنبؤ.

## 14 التقنيات

| التقنية | الإصدار في `requirements.txt` |
| --- | --- |
| Flask | 3.0.0 |
| scikit-learn | 1.3.2 |
| pandas | 2.1.4 |
| numpy | 1.26.2 |

التخزين: SQLite عبر `sqlite3` في المكتبة القياسية. القوالب: Jinja2 المدمج مع Flask. لا يوجد `package.json`.

## 15 شجرة الملفات

```
StentVision/
├── app.py
├── database.db
├── requirements.txt
├── README.md
├── assets/
│   ├── fonts/          IBM Plex Sans Arabic
│   └── images/Logo.jpeg
├── data/sample_sensor_data.csv
├── models/
│   ├── risk_model.py
│   ├── risk_model.pkl
│   └── scaler.pkl
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── history.html
    ├── alerts.html
    └── settings.html
```

## 16 الواجهة الأمامية

قوالب Jinja: `base.html` ثم لوحة وسجل وتنبيهات وإعدادات. التنسيق في `static/css/style.css` والسلوك في `static/js/main.js`. الخطوط العربية ملفات محلية داخل `assets/fonts`. الشعار `assets/images/Logo.jpeg`.

استنتاج من الكود: الصفحات الأربع دوال `render_template` فقط، والبيانات الحية تصل عبر طلبات JSON إلى مسارات `/api`.

## 17 الخادم الخلفي

تطبيق Flask واحد في `app.py`. الاتصال بقاعدة البيانات يفتح ملفاً في كل دالة عبر `get_db()` ويغلقه بعد الاستعلام. التنبؤ يمر عبر `save_reading_and_prediction`.

## 18 تدفق الطلب

```
POST /api/reading
  -> قراءة JSON
  -> تحويل الحقول الأربعة إلى float
  -> INSERT sensor_readings
  -> predict_risk
  -> INSERT predictions
  -> INSERT alerts إذا should_alert
  -> JSON بالنتيجة والوصف
```

قيم غير رقمية ترجع الحالة 400 والنص «قيم غير صالحة». جسم فارغ يرجع 400 والنص «بيانات غير صالحة».

## 19 قاعدة البيانات

المحرك SQLite. الملف `database.db`. الجداول تُنشأ بـ `CREATE TABLE IF NOT EXISTS` داخل `init_db`. لا توجد تهجيرات لاحقة في الملفات الحالية.

فهارس إضافية: غير موجود في الملفات الحالية.

## 20 نقاط النهاية

| الطريقة | المسار | الوظيفة |
| --- | --- | --- |
| GET | `/` | لوحة التحكم |
| GET | `/history` | السجل |
| GET | `/alerts` | التنبيهات |
| GET | `/settings` | الإعدادات |
| POST | `/api/reading` | حفظ قراءة |
| POST | `/api/reading/simulate` | محاكاة |
| GET | `/api/readings?limit=` | قراءات، الافتراضي 100 |
| GET | `/api/readings/latest` | آخر 4 قراءات بالترتيب الزمني التصاعدي بعد العكس |
| GET | `/api/chart/flow` | آخر 50 تدفقاً |
| GET | `/api/chart/pressure` | آخر 50 فرق ضغط |
| GET | `/api/chart/risk` | آخر 50 درجة خطر |
| GET | `/api/risk/current` | آخر تنبؤ أو أصفار ووصف «لا توجد قراءات حتى الآن.» |
| GET | `/api/alerts` | آخر 20 تنبيهاً |
| POST | `/api/train` | إعادة التدريب |

## 21 المصادقة

غير موجود في الملفات الحالية. لا جلسات ولا كلمات مرور.

## 22 الأمان

| الموجود | التفصيل |
| --- | --- |
| استعلامات بمعاملات | `?` في عبارات INSERT وSELECT |
| رفض JSON الناقص | استجابة 400 |

| غير الموجود | |
| --- | --- |
| تسجيل دخول | غير موجود في الملفات الحالية |
| CSRF | غير موجود في الملفات الحالية |
| تحديد معدل الطلبات | غير موجود في الملفات الحالية |
| إخفاء وضع التصحيح | `debug=True` في `app.run` |
| تقييد المضيف | المضيف `0.0.0.0` فيستمع على كل الواجهات المحلية للشبكة |

`POST /api/train` يعيد نص الاستثناء في الحقل `error` عند الفشل.

## 23 الإعدادات

| البند | القيمة في الكود |
| --- | --- |
| مسار القاعدة | `database.db` بجانب `app.py` |
| المنفذ | 5000 |
| المضيف | `0.0.0.0` |
| التصحيح | `True` |
| عتبة التحذير | 40 |
| عتبة الحرج | 70 |
| ملف البيانات | `data/sample_sensor_data.csv` |

متغيرات بيئة: غير موجود في الملفات الحالية.

## 24 التكاملات الخارجية

غير موجود في الملفات الحالية كعميل HTTP داخل بايثون. التكامل المتوقع جهاز يرسل إلى `/api/reading`.

## 25 المهام والجدولة

غير موجود في الملفات الحالية. التدريب يحدث عند الإقلاع أو عند `POST /api/train` فقط.

## 26 الملفات المهمة

| الملف | ملاحظة |
| --- | --- |
| `database.db` | بيانات التشغيل المحلية |
| `models/risk_model.pkl` | نموذج محفوظ بـ pickle |
| `models/scaler.pkl` | مقياس محفوظ بـ pickle |
| `data/sample_sensor_data.csv` | لازم للتدريب |

## 27 السجلات

تسجيل إلى ملف log: غير موجود في الملفات الحالية. أخطاء التدريب ترجع في JSON. تشغيل Flask مع `debug=True` يطبع سجل الخادم في الطرفية.

## 28 التثبيت

من مجلد المشروع `D:\VSCode\Projects\StentVision`:

```
pip install -r requirements.txt
python app.py
```

ثم فتح `http://127.0.0.1:5000`.

## 29 دليل التطوير

- مسارات الصفحات والـ API في `app.py`.
- منطق الخطر في `predict_risk` داخل `models/risk_model.py`.
- أعمدة التدريب يجب أن تبقى `flow_rate,p1,p2,delta_p,label`.
- عند الإقلاع يُعاد تدريب النموذج ويُستبدل الملفان `pkl`.

اختبارات آلية: غير موجود في الملفات الحالية.

## 30 النشر

ملف نشر (Dockerfile أو Procfile أو منصة سحابية): غير موجود في الملفات الحالية. التشغيل الموثق في الكود هو `app.run` محلياً.

## 31 النسخ الاحتياطي

انسخ `database.db` إن أردت الإبقاء على القراءات. نسخ `risk_model.pkl` و`scaler.pkl` يحفظ النموذج الحالي إلى أن يُعاد التدريب. إجراء نسخ مجدول: غير موجود في الملفات الحالية.

## 32 استكشاف الأخطاء

| العرض | السبب في الكود |
| --- | --- |
| فشل الإقلاع بسبب ملف البيانات | `DATA_PATH` غير موجود |
| 400 على `/api/reading` | JSON غائب أو قيم غير رقمية |
| خطر صفري ووصف عدم وجود قراءات | جدول `predictions` فارغ |
| المنفذ مشغول | المنفذ ثابت 5000 |

## 33 الاعتماديات

من `requirements.txt`: Flask 3.0.0، scikit-learn 1.3.2، pandas 2.1.4، numpy 1.26.2. SQLite ضمن بايثون.

## 34 القيود

- التصنيف ثنائي على بيانات CSV محلية، والنتيجة درجة احتمال وليست تشخيصاً سريرياً موثقاً في الملفات.
- لا مصادقة.
- وضع التصحيح مفعّل والمضيف مفتوح على كل الواجهات.
- إعادة التشغيل تعيد التدريب من CSV.
- لا ربط جهاز داخل المستودع.

## 35 الحالة الحالية

التطبيق يشتغل كخادم Flask مع قاعدة `database.db` موجودة في الجذر، ونموذج `pkl` ومقياس محفوظان في `models/`. الصفحات الأربع والقوالب والملف الثابت CSS/JS موجودة.

## 36 القرارات

| القرار | أين يظهر |
| --- | --- |
| غابة عشوائية مع توحيد قياسي | `risk_model.py` |
| عتبات 40 و70 | ثوابت `WARNING_THRESHOLD` و`CRITICAL_THRESHOLD` |
| SQLite ملف واحد | `DB_PATH` |
| بذرة عشوائية 42 | `train_test_split` والنموذج |

تناقض مع README السابق: المسار المكتوب سابقاً `D:\VSCode\Projects\StentVisioni` واسم المجلد في الشجرة `StentVisioni/`. المجلد الحالي اسمه `StentVision`. الشجرة السابقة وضعت الخطوط تحت `static/assets`. الملفات الحالية تضع الخطوط والشعار تحت `assets/` في الجذر، و`static` فيه `css` و`js` فقط.

## 37 الاختبار

اختبارات وحدة: غير موجود في الملفات الحالية. المسار `POST /api/reading/simulate` يوفّر قراءة تجريبية بقيم افتراضية.

## 38 متطلبات التشغيل

مفسر بايثون قادر على تثبيت الإصدارات في `requirements.txt`. إصدار بايثون مثبت داخل المشروع: غير موثق. نظام تشغيل مناسب لتشغيل Flask محلياً. متصفح لفتح المنفذ 5000.

## 39 سجل التغييرات

غير موجود في الملفات الحالية. لا يوجد رقم إصدار في `requirements.txt` أو `app.py`.

## System Overview

نظام محلي: متصفح، خادم Flask على المنفذ 5000، نموذج تصنيف، وملف SQLite لثلاث جداول (قراءات، تنبؤات، تنبيهات).

## Quick Reference

| البند | القيمة |
| --- | --- |
| التشغيل | `python app.py` |
| العنوان | `http://127.0.0.1:5000` |
| القاعدة | `database.db` |
| التدريب | `data/sample_sensor_data.csv` |
| إدخال الجهاز | `POST /api/reading` |

## Quick Start

```
cd D:\VSCode\Projects\StentVision
pip install -r requirements.txt
python app.py
```

افتح `http://127.0.0.1:5000`. لمحاكاة قراءة أرسل POST إلى `/api/reading/simulate`.

## For Non-Technical Users

التطبيق يعرض أرقاماً عن تدفق الدم وضغطه حول الدعامة، ثم يلوّن الحالة: طبيعي، أو تحذير، أو خطر. التحذير يبدأ عند درجة 40، والخطر عند 70. النصوص الجاهزة تطلب متابعة طبية في التحذير، وفحصاً طبياً فورياً في الخطر. هذه النصوص مخرجات النموذج البرمجي داخل المشروع.

## For Developers

ابدأ من `save_reading_and_prediction` ثم `predict_risk`. أي عمود جديد في CSV يحتاج تعديلاً في قائمة الأعمدة داخل `load_and_train_model` و`predict_risk` معاً. واجهة المتصفح تستهلك JSON من مسارات `/api`.
