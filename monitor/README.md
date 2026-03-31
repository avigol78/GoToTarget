# ניטור מרכז השיחות – ערן

אפליקציה לניטור נתוני מרכז השיחות של ער"ן לאורך זמן וסיכום שבועי.

## התקנה

```bash
pip install playwright matplotlib
playwright install chromium
```

## שימוש

### 1. כניסה ראשונית (פעם אחת)
```bash
python -m monitor.main login
```
* יפתח דפדפן – מלא אימייל וסיסמא
* סמן "כניסה ללא שלוחה"
* השלם reCAPTCHA
* הזן את הקוד שהגיע ב-SMS/מייל
* לאחר שהדף נטען – חזור לטרמינל ולחץ Enter
* הסשן נשמר ב-`eran_session.json`

### 2. התחלת ניטור
```bash
python -m monitor.main collect
```
מדגם כל 5 דקות (ניתן לשנות עם `ERAN_POLL_INTERVAL=120`).  
לעצירה: Ctrl+C

### 3. הפקת דוח שבועי
```bash
python -m monitor.main report
python -m monitor.main report --days 3 --chart chart.png
```

### 4. ייצוא ל-CSV
```bash
python -m monitor.main export --out data.csv
```

## משתני סביבה

| משתנה               | ברירת מחדל        | תיאור                          |
|---------------------|-------------------|-------------------------------|
| `ERAN_EMAIL`        | ""                | אימייל לכניסה                 |
| `ERAN_PASSWORD`     | ""                | סיסמא (לא חובה, ניתן להזין ידנית) |
| `ERAN_POLL_INTERVAL`| 300               | זמן בין מדגמים (שניות)        |
| `ERAN_DB_PATH`      | eran_monitor.db   | נתיב לבסיס הנתונים            |
| `ERAN_SESSION_FILE` | eran_session.json | נתיב לקובץ הסשן               |

## הנתונים שנאספים

| שדה        | תיאור                          |
|------------|-------------------------------|
| `calls`    | מספר שיחות פעילות              |
| `waiting`  | פונים ממתינים                  |
| `connected`| מתנדבים מחוברים                |
| `on_break` | מתנדבים בהפסקה                 |

## הדוח

הדוח מחשב **פער = היצע − ביקוש** לכל מדגם:
* **היצע** = מחוברים − בהפסקה
* **ביקוש** = שיחות + ממתינים

פער שלילי = מחסור במתנדבים; פער חיובי = עודף.
