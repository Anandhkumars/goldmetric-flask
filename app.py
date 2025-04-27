from flask import Flask, render_template, request, jsonify, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, send_file
from apscheduler.triggers.cron import CronTrigger
from flask import session, redirect, url_for
from flask import Flask, jsonify, send_file
from flask import Flask, render_template
from datetime import datetime, timedelta
from flask_cors import CORS
from fpdf import FPDF
import pywhatkit as kit
import bcrypt
import sqlite3
import requests
import sqlite3
import hashlib
import datetime
import jwt
import os

app = Flask(__name__, template_folder="templates")
CORS(app) 

DATABASE = "goldmetric.db"
app.secret_key = "b704225a68abe5f9c5aa7ebd680cf893" 

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(username):
    payload = {
        "username": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=3)  
    }
    return jwt.encode(payload, app.secret_key, algorithm="HS256")

def init_db():
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS name_mobile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            gold_weight REAL NOT NULL,
            status TEXT DEFAULT 'Pending'  -- New status column (default: Pending)
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calculation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        party_gold1 REAL,
        party_gold2 REAL,
        pure_gold1 REAL,
        pure_gold2 REAL,
        result1 REAL,
        result2 REAL,
        added_pure_weight REAL,
        party_gold REAL,
        pure_weight REAL,
        remaining_gold REAL,
        fineness_percentage REAL,
        fineness_karat REAL,
        FOREIGN KEY (user_id) REFERENCES name_mobile(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_rate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            day TEXT NOT NULL,
            price INTEGER NOT NULL
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        gold_price REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES login(id) ON DELETE CASCADE
    );
""")
    cursor.execute("SELECT COUNT(*) FROM settings WHERE id = 1")
    exists = cursor.fetchone()[0]

    if not exists:
        cursor.execute("INSERT INTO settings (id, user_id, gold_price) VALUES (?, ?, ?)", (1, 1, 100.0))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER NOT NULL,
           amount REAL NOT NULL,
           payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'Online', 'Pending')) DEFAULT 'Pending',
           payment_status TEXT NOT NULL CHECK(payment_status IN ('Pending', 'Completed')) DEFAULT 'Pending',
           date TEXT DEFAULT (datetime('now', 'localtime')),
           FOREIGN KEY (user_id) REFERENCES name_mobile(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT * FROM login WHERE username = 'admin' OR phone = '9843058437'")
    if not cursor.fetchone(): 
       default_admin_password = hash_password("admin123")
       cursor.execute("""
          INSERT INTO login (username, email, phone, password)
          VALUES (?, ?, ?, ?)
    """, ("admin", "admin@example.com", "9843058437", default_admin_password))
    conn.commit()
    print("Default admin user created.")

    conn.commit()
    conn.close()

init_db() 

#pages
@app.route("/")
def index():
    return render_template("index.html") 

@app.route('/dashboard')
def dashboard_page():
    conn = sqlite3.connect('goldmetric.db')  
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, mobile FROM name_mobile WHERE status = 'Pending' ORDER BY id DESC")
    orders = [{"bill_number": row[0], "name": row[1], "mobile": row[2]} for row in cursor.fetchall()]  

    conn.close()

    return render_template("Dashboard.html", orders=orders)

@app.route('/logout')  
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/purity_calc')
def purity_calc():
    return render_template('PurityCalc.html')

@app.route('/pending_payments')
def pending_payments():
    return render_template('PendingPayments.html')

@app.route('/customer_history')
def customer_history():
    return render_template('CustomerHistory.html')

@app.route('/weekly_overview')
def weekly_overview():
    return render_template('Weeklyover.html')

@app.route('/settings')
def settings():
    return render_template('Settings.html')


@app.route('/calculation')
def calculation_page():
    record_id = request.args.get('id')
    mobile = request.args.get('mobile')
    return render_template('calculation.html', record_id=record_id, mobile=mobile)

@app.route('/calculate_purity_page')
def calculate_purity_page():
    bill = request.args.get('bill')
    mobile = request.args.get('mobile')

    if not bill or not mobile:
        return "Invalid parameters", 400  

    return render_template("calculation.html", bill=bill, mobile=mobile)


@app.route('/gold_purity_dtls')
def gold_purity_dtls():
    return render_template('GoldPuritydtls.html')

@app.route('/forgot_password')
def forgot_password():
    return render_template('Forgotpass.html')

@app.route('/forgotpass')
def forgotpass():
    return render_template("forgotpass.html")

@app.route('/resetpass')
def resetpass():
    return render_template("resetpass.html")

@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")  

app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

#login page module
@app.route("/api/login", methods=["POST"])  
def login_api():
    try:
        data = request.get_json()
        identifier = data.get("identifier") 
        password = data.get("password")
        hashed_password = hash_password(password)

        if not identifier or not password:
            return jsonify({"status": "error", "message": "All fields are required"}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username FROM login 
                WHERE (username = ? OR email = ? OR phone = ?) 
                AND password = ?
            """, (identifier, identifier, identifier, hashed_password))
            user = cursor.fetchone()

        if user:
            session["username"] = user["username"]
            return jsonify({"status": "success", "message": "Login successful", "username": user["username"]}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Forgot password module
@app.route("/check-email", methods=["POST"])
def check_email():
    try:
        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"status": "error", "message": "Email is required"}), 400

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM login WHERE email = ?", (email,))
            user = cursor.fetchone()

        if user:
            return jsonify({"status": "success", "message": "Email exists"}), 200
        else:
            return jsonify({"status": "error", "message": "Email not found"}), 404

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Reset Password module
@app.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json()
        email = data.get("email")
        new_password = data.get("new_password")

        if not email or not new_password:
            return jsonify({"status": "error", "message": "Email and new password are required"}), 400

        hashed_password = hash_password(new_password)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM login WHERE email = ?", (email,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"status": "error", "message": "Email not found"}), 404

            cursor.execute("UPDATE login SET password = ? WHERE email = ?", (hashed_password, email))
            conn.commit()

        return jsonify({"status": "success", "message": "Password updated successfully!"}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


#Store the data for name_mobile table
@app.route('/store_data', methods=['POST'])
def store_data():
    try:
        if not request.is_json:
            return jsonify({"success": False, "message": "Invalid Content-Type, expected application/json"}), 415

        data = request.get_json()
        name = data.get("name")
        mobile = data.get("mobile")
        gold_weight = data.get("gold_weight")

        if not name or not mobile or not gold_weight:
            return jsonify({"success": False, "message": "Missing fields"}), 400

        conn = sqlite3.connect("goldmetric.db")
        cursor = conn.cursor()

        cursor.execute("SELECT status FROM name_mobile WHERE mobile = ?", (mobile,))
        existing_row = cursor.fetchone()

        if existing_row:
            status = existing_row[0]
            if status == "Pending":
                conn.close()
                return jsonify({"success": False, "message": "Duplicate entry not allowed. Mobile number already exists with status 'Pending'"}), 409

        cursor.execute("INSERT INTO name_mobile (name, mobile, gold_weight, status) VALUES (?, ?, ?, ?)",
                       (name, mobile, gold_weight, "Pending"))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Data stored successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



# display Only Pending Data for calculation part
@app.route('/get_pending_data', methods=['GET'])
def get_pending_data():
    try:
        conn = sqlite3.connect("goldmetric.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, mobile, gold_weight, status FROM name_mobile WHERE status = 'Pending'")
        data = cursor.fetchall()
        conn.close()

        data_list = [{"id": row[0], "name": row[1], "mobile": row[2], "gold_weight": row[3], "status": row[4]} for row in data]
        return jsonify({"success": True, "data": data_list}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



# calculation Module
@app.route("/calculate", methods=["POST"])
def calculate():
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Invalid Content-Type, expected application/json"}), 415

        data = request.get_json()
        mobile = data.get("mobile")

        if not mobile:
            return jsonify({"success": False, "error": "Mobile number is required"}), 400

        conn = sqlite3.connect("goldmetric.db")
        cursor = conn.cursor()
        cursor.execute("SELECT gold_price FROM settings WHERE id = 1")
        gold_price_row = cursor.fetchone()

        if not gold_price_row or gold_price_row[0] is None:
            return jsonify({"success": False, "error": "Gold price is not set in settings table"}), 500

        gold_price = float(gold_price_row[0]) 

        cursor.execute("""SELECT id, name, gold_weight FROM name_mobile WHERE mobile = ? ORDER BY id DESC LIMIT 1""", (mobile,))
        user = cursor.fetchone()


        if not user or any(value is None for value in user):
            return jsonify({"success": False, "error": "Mobile number not found or data missing"}), 404

        user_id, name, gold_weight = user
        try:
            party_gold = float(gold_weight or 0)
            party_gold1 = float(data.get("party_gold1", 0) or 0)
            party_gold2 = float(data.get("party_gold2", 0) or 0)
            pure_gold1 = float(data.get("pure_gold1", 0) or 0)
            pure_gold2 = float(data.get("pure_gold2", 0) or 0)
            result1 = float(data.get("result1", 0) or 0)
            result2 = float(data.get("result2", 0) or 0)
            added_pure_weight = float(data.get("added_pure_weight", 0) or 0)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid input values"}), 422

        total_party_gold = party_gold1 + party_gold2
        total_pure_gold = pure_gold1 + pure_gold2
        gold_ratio = round((total_pure_gold / total_party_gold) * 100, 2) if total_party_gold else 0

        final_value = ((result1 + result2) / 4) * gold_ratio
        res1_value = (result1 / 4) * gold_ratio
        res2_value = (result2 / 4) * gold_ratio

        def custom_round(value):
            first_digit=int(str(value)[0])
            second_digit=int(str(value)[1])

            if second_digit == 9:
                return first_digit + 1
            else:
                return first_digit

        final_value_rounded = custom_round(final_value)
        res1_value_rounded = custom_round(res1_value)
        res2_value_rounded = custom_round(res2_value)

        pure_gold1_updated = pure_gold1 + res1_value_rounded
        pure_gold2_updated = pure_gold2 + res2_value_rounded
        total_pure_gold_updated = total_pure_gold + final_value_rounded

        result_party_gold1 = round((pure_gold1_updated / party_gold1) * 100, 2) if party_gold1 else 0
        result_party_gold2 = round((pure_gold2_updated / party_gold2) * 100, 2) if party_gold2 else 0
        average_result = round((result_party_gold1 + result_party_gold2) / 2, 2)

        party_gold -= 100
        added_pure_weight += 100

        calculated_value = (total_pure_gold_updated - added_pure_weight) / average_result if average_result else 0
        calculated_value_final = int(str(calculated_value).replace('.', '')[:3])
        final_party_gold = total_party_gold - calculated_value_final

        
        remaining_gold = final_party_gold - total_pure_gold_updated
        fineness_percentage = round((added_pure_weight / final_party_gold) * 100, 4) if final_party_gold else 0
        fineness_karat = round(fineness_percentage / 4.166, 2)

        amount = gold_price

        final_party_gold = round(final_party_gold / 10000, 4)
        total_pure_gold_updated = round(total_pure_gold_updated / 10000, 4)
        remaining_gold = round(remaining_gold / 10000, 4)

        cursor.execute("""
             INSERT INTO calculation (user_id, party_gold1, party_gold2, pure_gold1, pure_gold2, result1, result2, 
                             added_pure_weight, party_gold, pure_weight, remaining_gold, 
                             fineness_percentage, fineness_karat)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
            user_id, party_gold1, party_gold2, pure_gold1, pure_gold2, result1, result2,
            added_pure_weight, final_party_gold, total_pure_gold_updated,
            remaining_gold, fineness_percentage, fineness_karat
        ))

        cursor.execute("""
            INSERT INTO payment (user_id, amount, payment_status, payment_method, date)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
        """, (user_id, amount, 'Pending', 'Pending'))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Calculation and payment stored successfully!",
            "user_id": user_id, 
            "name": name,
            "mobile": mobile,
           "party_gold": final_party_gold,
           "pure_weight": total_pure_gold_updated,
           "remaining_gold": remaining_gold,
           "fineness_percentage": fineness_percentage,
           "fineness_karat": fineness_karat,
           "gold_price": gold_price,
           "amount": amount
        }), 200

    except sqlite3.Error as e:
        return jsonify({"success": False, "error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if conn:
            conn.close()  


#update the status for name_mobile table    
@app.route('/update_status', methods=['POST'])
def update_status():
    try:
        data = request.get_json()
        name = data.get("name")
        mobile = data.get("mobile")
        new_status = data.get("status")

        if not name or not mobile or not new_status:
            return jsonify({"success": False, "message": "Missing fields"}), 400

        conn = sqlite3.connect("goldmetric.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM name_mobile WHERE name = ? AND mobile = ?", (name, mobile))
        result = cursor.fetchone()

        if not result:
            return jsonify({"success": False, "message": "No matching record found"}), 404

        user_id = result[0]  
        cursor.execute("UPDATE name_mobile SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "Status updated successfully", "id": user_id}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



#display the view page in view page table
@app.route('/get_calculations', methods=['GET'])
def get_calculations():
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nm.name, nm.mobile, c.party_gold, c.pure_weight, 
               c.remaining_gold, c.fineness_percentage, c.fineness_karat
        FROM calculation c
        JOIN name_mobile nm ON c.user_id = nm.id
    """)
    data = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    
    conn.close()
    return jsonify(data)



#display quick access table
@app.route('/get_pending_orders', methods=['GET'])
def get_pending_orders():
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, mobile FROM name_mobile WHERE status = 'Pending'")  
    orders = [{"bill_number": row[0], "name": row[1], "mobile": row[2]} for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({"orders": orders})



#dasbboard module
DB_NAME = "goldmetric.db"
API_URL = "https://www.goldapi.io/api/XAU/INR"
API_KEY = "" #goldapi-1f5iujsm87i5bf0-io ---->use this api

@app.route("/api/goldrate", methods=["GET"])
def get_gold_rate():
    """ Fetch gold rate from API and return price per gram """
    try:
        headers = {
            "x-access-token": API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(API_URL, headers=headers)
        data = response.json()

        if "price" in data:
            price_per_ounce = data["price"]
            price_per_gram = price_per_ounce / 31.1035 

            return jsonify({"rate": round(price_per_gram, 2)})
        else:
            return jsonify({"error": "Invalid API response"}), 500

    except Exception as e:
        return jsonify({"error": f"Failed to fetch gold rate: {str(e)}"}), 500
    
def fetch_and_store_gold_rate():
    """ Fetch gold rate from API, convert to grams, and store in DB daily """
    try:
        headers = {
            "x-access-token": API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.get(API_URL, headers=headers)
        data = response.json()

        if "price" in data:
            price_per_ounce = data["price"]  
            price_per_gram = round(price_per_ounce / 31.1035, 2)  

            date = datetime.date.today().strftime("%Y-%m-%d")  
            day = datetime.datetime.today().strftime("%A")  

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO gold_rate (date, day, price) VALUES (?, ?, ?)", (date, day, price_per_gram))

            conn.commit()
            conn.close()
            print(f"Gold Rate Stored: {date} ({day}) - ₹ {price_per_gram} per gram")

        else:
            print("Error: Invalid API Response -", data)

    except Exception as e:
        print("Error fetching gold rate:", e)

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_store_gold_rate, CronTrigger(hour=10, minute=00))
scheduler.start()

@app.route("/api/gold_fluctuation", methods=["GET"])
def get_gold_fluctuation():
    """Fetch last 7 days of gold prices from the database"""
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT day, price FROM gold_rate ORDER BY date ASC LIMIT 7")
    data = cursor.fetchall()
    conn.close()

    if data:
        days = [row[0] for row in data]
        prices = [row[1] for row in data]
        return jsonify({"days": days, "prices": prices})
    else:
        return jsonify({"error": "No gold rate data available"}), 404



#pending Payment Module
@app.route('/pending-payments', methods=['GET'])
def get_pending_payments():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.id AS payment_id,
            p.user_id,
            n.name,
            n.gold_weight,
            c.fineness_percentage,
            p.amount,
            p.payment_status
        FROM payment p
        JOIN name_mobile n ON p.user_id = n.id
        JOIN calculation c ON p.user_id = c.user_id
        WHERE p.payment_status = 'Pending'
    """)
    
    pending_payments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(pending_payments)



#API to update payment status to "Completed"
@app.route('/update-payment-status', methods=['POST'])
def update_payment_status():
    data = request.json
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "Payment ID is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE payment SET payment_status = 'Completed' WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    return jsonify({"message": "Payment status updated successfully"})



#Customer history module
@app.route('/search_customer', methods=['GET'])
def search_customer():
    query = request.args.get('query', '').strip().lower()

    if not query:
        return jsonify({"message": "Please enter a valid search term"}), 400

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row  
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT nm.id, nm.name, nm.mobile, nm.gold_weight, c.fineness_percentage, p.amount, p.payment_status, p.date FROM name_mobile nm LEFT JOIN calculation c ON nm.id = c.user_id LEFT JOIN payment p ON nm.id = p.user_id WHERE LOWER(nm.name) LIKE ? OR nm.id LIKE ?", (f"%{query}%", f"%{query}%"))
        results = cursor.fetchall()

        if not results:
            return jsonify({"message": "No results found"}), 404

        customer_list = []
        for row in results:
            customer_list.append({
                "user_id": row["id"],  
                "name": row["name"],
                "mobile": row["mobile"],
                "gold_weight": row["gold_weight"],
                "purity": row["fineness_percentage"],
                "amount": row["amount"],
                "status": row["payment_status"],
                "date": row["date"].split(" ")[0] if row["date"] else None  
            })

        return jsonify(customer_list)

    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


#Settings Module
@app.route('/update-settings', methods=['POST'])
def update_settings():
    data = request.json
    username = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    new_password = data.get("newPassword")
    gold_price = data.get("goldPrice")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM login LIMIT 1")
    user = cursor.fetchone()

    if user:
        user_id = user[0]
        update_fields = []
        update_values = []

        if username:
            update_fields.append("username = ?")
            update_values.append(username)

        if email:
            update_fields.append("email = ?")
            update_values.append(email)

        if phone:
            update_fields.append("phone = ?")
            update_values.append(phone)

        if new_password:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            update_fields.append("password = ?")
            update_values.append(hashed_password)

        if update_fields:
            update_query = f"UPDATE login SET {', '.join(update_fields)} WHERE id = ?"
            update_values.append(user_id)
            cursor.execute(update_query, update_values)

        cursor.execute("SELECT id FROM settings WHERE user_id = ?", (user_id,))
        settings = cursor.fetchone()

        if settings:
            cursor.execute("UPDATE settings SET gold_price = ? WHERE user_id = ?",
                           (gold_price, user_id))
        else:
            default_gold_price = 500 
            cursor.execute("INSERT INTO settings (user_id, gold_price) VALUES (?, ?)",
                           (user_id, default_gold_price))

        conn.commit()
        conn.close()
        return jsonify({"message": "Settings updated successfully!"})
    
    else:
        return jsonify({"error": "Admin user not found!"}), 404


#billing page 
def get_bill_details(user_id):
    conn = sqlite3.connect("goldmetric.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT n.name, c.user_id, c.fineness_percentage, c.fineness_karat, 
               c.party_gold, c.pure_weight, c.remaining_gold
        FROM calculation c
        JOIN name_mobile n ON c.user_id = n.id
        WHERE c.user_id = ?
    """, (user_id,))
    
    data = cursor.fetchone()
    conn.close()

    if data:
        return {
            "name": data["name"],
            "token_no": data["user_id"],
            "date": datetime.datetime.now().strftime("%d-%m-%Y"),
            "fineness_percentage": str(data["fineness_percentage"]),
            "fineness_karat": str(data["fineness_karat"]),
            "party_gold": str(data["party_gold"]),
            "pure_weight": str(data["pure_weight"]),
            "remaining_gold": str(data["remaining_gold"])
        }
    
    return None
class PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

@app.route("/generate_bill/<int:id>")
def generate_bill(id):
    data = get_bill_details(id)
    if not data:
        return jsonify({"error": "Invalid ID"}), 404

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    def add_bill_copy(title, y_offset):
        pdf.set_xy(10, y_offset)
        pdf.set_fill_color(200, 230, 255) 
        pdf.rect(10, y_offset, 190, 110, style='F')

        pdf.set_draw_color(0, 0, 139)
        pdf.set_line_width(0.8) 
        pdf.rect(10, y_offset, 190, 110, style='D') 

        image_width = 25
        image_height = 25
        image_y = y_offset + 2

        left_image_x = 12
        pdf.image("static/images/vivekananda.png", left_image_x, image_y, image_width, image_height)

        pdf.set_draw_color(0, 0, 139)  
        pdf.set_line_width(0.5)      
        pdf.rect(left_image_x, image_y, image_width, image_height)
        right_image_x = 173
        pdf.image("static/images/lab.jpg", right_image_x, image_y, image_width, image_height)
        pdf.rect(right_image_x, image_y, image_width, image_height)


        pdf.set_xy(40, y_offset + 2)
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(130, 7, "VIVEKANANDHA GOLD TESTING CENTRE", ln=True, align="C")
        pdf.set_text_color(0, 0, 139)

        pdf.set_font("Arial", "B", 12)
        pdf.set_xy(40, y_offset + 10)
        pdf.cell(130, 5, "151, South Car Street, Sivakasi - 626123", ln=True, align="C")

        pdf.set_xy(40, y_offset + 15)
        pdf.cell(130, 5, "Cell: 98430 58437", ln=True, align="C")
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(255, 0, 0)
        pdf.set_text_color(255, 255, 255)
        pdf.set_x((210 - 120) / 2 + 23)
        pdf.cell(70, 5, title, ln=True, align="C", fill=True)
        pdf.set_text_color(0, 0, 139)
        pdf.ln(5)

        pdf.set_line_width(0.8) 
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Arial", "B", 12)

        party_name_text = f"     PARTY NAME : {data['name']}"
        party_name_width = pdf.get_string_width(party_name_text) + 5

        pdf.set_x(10 + 5)
        pdf.cell(party_name_width, 10, party_name_text, border=0)
        space_between = 10  
        remaining_width = 190 - party_name_width - space_between
        pdf.cell(space_between, 10, "", border=0) 
        pdf.cell(remaining_width / 2, 10, f"    DATE : {data['date']}", border=0)
        pdf.cell(remaining_width / 2 , 10, f"   TOKEN NO : {data['token_no']}", border=0) 
        pdf.ln(12)
        
        pdf.set_line_width(0.8) 
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_x(10 + 22)
        pdf.cell(95, 8, f"FINENESS IN % : {data['fineness_percentage']}%", border=0)
        pdf.cell(95, 8, f"FINENESS IN KT : {data['fineness_karat']}", border=0)
        pdf.ln(10)

        pdf.set_line_width(0.8) 
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(1)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(190, 10, "SPECIAL INFORMATION", ln=True, align="C")
        pdf.set_font("Arial", "B", 12)

        pdf.set_x(10 + 13)
        pdf.cell(63, 8, f"GOLD WT : {data['party_gold']}", border=0)
        pdf.cell(63, 8, f"PURE WT : {data['pure_weight']}", border=0)
        pdf.cell(63, 8, f"REMAINS : {data['remaining_gold']}", border=0)
        pdf.ln(15)

        pdf.set_line_width(0.8) 
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        pdf.set_font("Arial", "B", 11)
        pdf.multi_cell(190, 5, "      NOTE: We are not responsible for any melting defect.\n                   We are not responsible for results variations.", align="L")
        pdf.cell(190, 6, "Checked by: _______________  ", ln=True, align='R')
        pdf.ln(10)

    add_bill_copy("TESTING REPORT", 10)
    add_bill_copy("TESTING REPORT", 140)

    import os

# System Downloads path
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

# File path inside Downloads
    file_path = os.path.join(downloads_folder, f"bill_{data['token_no']}.pdf")

# Create Downloads folder if not exists (normally already exists)
    if not os.path.exists(downloads_folder):
        os.makedirs(downloads_folder)

# Check if PDF already exists → remove it
    if os.path.exists(file_path):
        try:
          os.remove(file_path)
        except PermissionError:
          return jsonify({
            "error": f"Please close the PDF file 'bill_{data['token_no']}.pdf' before generating a new one."
        }), 500

# Try to output PDF
    try:
       pdf.output(file_path)
    except PermissionError:
       return jsonify({
            "error": "Permission denied while saving the PDF. Make sure the file is not open or locked."
    }), 500

# Return the file for download
    return send_file(file_path, mimetype="application/pdf", as_attachment=True, download_name=f"bill_{data['token_no']}.pdf")

#weekly overview modules
DB_PATH = "goldmetric.db"

def get_weekly_data(start_date=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if not start_date:
        end_date = datetime.date.today()
        start_date = end_date - timedelta(days=6)
    else:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = start_date + timedelta(days=6)

    cursor.execute("""
        SELECT DATE(date) as date, 
               COALESCE(SUM(amount), 0) as total_revenue, 
               COUNT(*) as test_count 
        FROM payment 
        WHERE DATE(date) BETWEEN ? AND ?
        GROUP BY DATE(date)
        ORDER BY DATE(date);
    """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

    revenue_data = cursor.fetchall()
    dates, revenue, tests = [], [], []

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        found = next((row for row in revenue_data if row[0] == date_str), None)
        
        dates.append(date_str)
        revenue.append(found[1] if found else 0)
        tests.append(found[2] if found else 0)
        
        current_date += timedelta(days=1)

    cursor.execute("""
        SELECT LOWER(payment_method), COUNT(*) 
        FROM payment 
        WHERE DATE(date) BETWEEN ? AND ?
        GROUP BY LOWER(payment_method);
    """, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

    payment_data = dict(cursor.fetchall()) 
    total_cash_count = payment_data.get("cash", 0)
    total_online_count = payment_data.get("online", 0)

    conn.close()

    return {
        "dates": dates,
        "revenue": revenue,
        "tests": tests,
        "totalCashCount": total_cash_count,
        "totalOnlineCount": total_online_count
    }

@app.route('/weekly-data', methods=['GET'])
def weekly_data():
    start_date = request.args.get('start_date')  
    return jsonify(get_weekly_data(start_date))
def get_user_id(name, mobile):
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM name_mobile WHERE name = ? AND mobile = ?", (name, mobile))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

#update payment status module
@app.route('/update_payment_method', methods=['POST'])
def update_payment_method():
    data = request.json
    name = data.get("name")
    mobile = data.get("mobile")
    method = data.get("method") 

    user_id = get_user_id(name, mobile)
    if not user_id:
        return jsonify({"success": False, "message": "User not found!"})

    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("UPDATE payment SET payment_method = ? WHERE user_id = ?", (method, user_id))
        conn.commit()
        conn.close()

        if method == "Online":
            return send_upi_whatsapp(name, mobile, user_id)

        return jsonify({"success": True, "message": "Payment method updated!"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# send payment link whatsapp
def send_upi_whatsapp(name, mobile, user_id):
    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT amount FROM payment WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return jsonify({"success": False, "message": "No amount found!"})

    amount = result[0]

    upi_name = name.replace(" ", "_")
    upi_id = "sa4562043@oksbi"
    upi_link = f"upi://pay?pa={upi_id}&pn={upi_name}&mc=0000&tid=123456&tr={amount}&tn=GoldPayment&am={amount}&cu=INR"

    message = (
        f"🔔 *VIVEKANANDHA GOLD TESTING CENTRE* 🔔\n\n"
        f"📢 *Payment Request for Gold Testing*\n"
        f"💰 *Amount Due:* ₹{amount}\n"
        f"💳 *Payment Mode:* Online\n\n"
        f"🔗 Click below to make payment:\n"
        f"{upi_link}\n\n"
        f"✅ Thank you for choosing our service!"
    )

    try:
        kit.sendwhatmsg_instantly(f"+91{mobile}", message, wait_time=10)
        return jsonify({"success": True, "message": "UPI link sent to WhatsApp!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/update_payment_status', methods=['POST'])
def update_payment_status_v2():
    data = request.json
    name = data.get("name")
    mobile = data.get("mobile")

    user_id = get_user_id(name, mobile)
    if not user_id:
        return jsonify({"success": False, "message": "User not found!"})

    conn = sqlite3.connect("goldmetric.db")
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE payment SET payment_status = 'Completed' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Payment status updated to Completed!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}) 
 

if __name__ == '__main__':
    app.run(debug=True)
