# Import stuff
from flask import Flask, render_template, request, session, url_for, redirect, flash
import pymysql.cursors
import pymysql
from pymysql.cursors import DictCursor
import hashlib
import datetime
import random
import json
import pdb

# Helper Functions ################################################################################
# Hashing for passwords
def pw2md5(pw):
    return hashlib.md5(pw.encode()).hexdigest()

# Generating time-based greeting messages
def greet_customer():
    day = datetime.datetime.today().weekday()
    hour = datetime.datetime.today().time().hour
    day_msg = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day]
    time_msg = "nighttime"
    if hour > 6:
        time_msg = "morning"
    if hour > 10:
        time_msg = "noon"
    if hour > 14:
        time_msg = "afternoon"
    if hour > 17:
        time_msg = "evening"
    if hour > 20:
        time_msg = "night"
    out_msg = "Happy {} {}."
    return out_msg.format(day_msg, time_msg)

def greet_agent():
    day = datetime.datetime.today().weekday()
    hour = datetime.datetime.today().time().hour
    day_msg = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day]
    time_msg = "nighttime"
    if hour > 6:
        time_msg = "morning"
    if hour > 10:
        time_msg = "noon"
    if hour > 14:
        time_msg = "afternoon"
    if hour > 17:
        time_msg = "evening"
    if hour > 20:
        time_msg = "night"
    out_msg = "It's {} {}."
    return out_msg.format(day_msg, time_msg)

# Authorising customers
def authorise_customer():
    try:
        email = session["email"]
        query = "SELECT * FROM customer WHERE email = %s"
        cursor = conn.cursor()
        cursor.execute(query, (email))
        data = cursor.fetchall()
        cursor.close()
        if data:
            return session["class"] == "customer"
        return False
    except:
        return False

# Fetch upcoming flights for customers (10 lines max)
def fetch_customer_upcoming():
    email = session["email"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE customer_email = %s AND status = "Upcoming" ORDER BY departure_time DESC LIMIT 10"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_customer_all():
    email = session["email"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE customer_email = %s ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_customer_available():
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, seats, seats - count(ticket_id) AS available_seats 
            FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = "Upcoming" GROUP BY airline_name, flight_num HAVING seats > count(ticket_id) ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    # Change flight_num to str for purchasing operation
    for row in data:
        for key in row.keys():
            row[key] = str(row[key])
    return data

def fetch_customer_spending():
    email = session["email"]
    query = """SELECT price, ticket_id, purchase_date 
               FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE customer_email = %s ORDER BY purchase_date ASC"""
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    if not data:
        return False, False, False, False
    months = []
    now = datetime.datetime.today().year*100 + datetime.datetime.today().month
    t = data[0]["purchase_date"].year*100 + data[0]["purchase_date"].month
    months.append(t)
    while t < now:
        if t % 100 == 12:
            t += 88
        t += 1
        months.append(t)
    spendings = [0 for _ in range(len(months))]
    for row in data:
        price = row["price"]
        month = row["purchase_date"].year*100 + row["purchase_date"].month
        m = months.index(month)
        spendings[m] += float(price)
    now = str(datetime.datetime.today().year) + "-" + str(datetime.datetime.today().month)
    past_year = datetime.datetime.today().year
    past_month = datetime.datetime.today().month - 6
    if past_month < 1:
        past_month += 12
        past_year -= 1
    past6m = str(past_year) + "-" + str(past_month)
    if len(now) < 7:
        now = now[:5] + "0" + now[-1]
    if len(past6m) < 7:
        past6m = past6m[:5] + "0" + past6m[-1]
    return months, spendings, now, past6m
    
# Authorising agents
def authorise_agent():
    try:
        email = session["email"]
        query = "SELECT * FROM booking_agent WHERE email = %s"
        cursor = conn.cursor()
        cursor.execute(query, (email))
        data = cursor.fetchall()
        cursor.close()
        if data:
            return session["class"] == "agent"
        return False
    except:
        return False

# Fetch stuff for agents
def fetch_agent_upcoming():
    book_id = session["book_id"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date, customer_email
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE booking_agent_id = %s AND status = "Upcoming" ORDER BY departure_time DESC LIMIT 10"""
    cursor = conn.cursor()
    cursor.execute(query, (book_id))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_agent_all():
    book_id = session["book_id"]
    query = """SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status, ticket_id, purchase_date, customer_email
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE booking_agent_id = %s ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (book_id))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_agent_commission():
    book_id = session["book_id"]
    query = """SELECT price, customer_email, purchase_date FROM flight NATURAL JOIN ticket NATURAL JOIN purchases
               WHERE booking_agent_id = %s ORDER BY purchase_date DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (book_id))
    data = cursor.fetchall()
    cursor.close()
    now = str(datetime.datetime.today().date())
    past30d = str(datetime.datetime.today().date() - datetime.timedelta(days=30))
    for row in data:
        for key in row.keys():
            row[key] = str(row[key])
            if key == "purchase_date":
                date_str = row[key]
                row[key] = date_str[:4] + date_str[5:7] + date_str[8:10]
    data = str(data)
    data = data.replace('\'','\"')
    return data, now, past30d

# Authorising staff
def authorise_staff():
    try:
        username = session["username"]
        query = "SELECT * FROM airline_staff WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username))
        data = cursor.fetchall()
        cursor.close()
        if data:
            return session["class"] == "staff"
        return False
    except:
        return False

# Fetch stuff for staff
def fetch_staff_upcoming():
    airline = session["airline"]
    query = """SELECT * FROM flight WHERE airline_name = %s AND status = "Upcoming" AND departure_time > "{}" ORDER BY departure_time DESC"""
    query = query.format(str(datetime.datetime.today())[:-7], str(datetime.datetime.today()+datetime.timedelta(days=30))[:-7])
    cursor = conn.cursor()
    cursor.execute(query, (airline))
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_staff_all():
    airline = session["airline"]
    query = """SELECT * FROM flight WHERE airline_name = %s ORDER BY departure_time DESC"""
    cursor = conn.cursor()
    cursor.execute(query, (airline))
    data = cursor.fetchall()
    cursor.close()
    for row in data:
        for key in row.keys():
            row[key] = str(row[key])
    return data

def fetch_staff_agent():
    airline = session["airline"]
    query = """SELECT booking_agent_id, email, SUM(price) * 0.1 AS commission
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases NATURAL JOIN booking_agent
            WHERE airline_name = "{}" AND purchase_date > "{}"
            GROUP BY booking_agent_id
            ORDER BY SUM(price) DESC LIMIT 5""".format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query)
    com_data = cursor.fetchall()
    query_temp = """SELECT booking_agent_id, email, COUNT(price) AS n_sales
                FROM flight NATURAL JOIN ticket NATURAL JOIN purchases NATURAL JOIN booking_agent
                WHERE airline_name = "{}" AND purchase_date > "{}"
                GROUP BY booking_agent_id
                ORDER BY COUNT(price) DESC LIMIT 5"""
    query_month = query_temp.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_year = query_temp.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor.execute(query_month)
    nsales_data_month = cursor.fetchall()
    cursor.execute(query_year)
    nsales_data_year = cursor.fetchall()
    cursor.close()
    return com_data, nsales_data_month, nsales_data_year

def fetch_staff_customer():
    airline = session["airline"]
    query = """SELECT email, name, COUNT(ticket_id)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases JOIN customer ON customer.email = purchases.customer_email
            WHERE airline_name = "{}" AND purchase_date > "{}"
            GROUP BY email
            ORDER BY COUNT(ticket_id) DESC
            LIMIT 5""".format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

def fetch_staff_destination():
    airline = session["airline"]
    query = """SELECT airport_city, COUNT(*)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, airport
            WHERE flight.arrival_airport = airport.airport_name AND airline_name = "{}" AND purchase_date > "{}"
            GROUP BY airport_city
            ORDER BY COUNT(*) DESC LIMIT 3"""
    query_3m = query.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=90))[:-7])
    query_12m = query.format(airline, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query_3m)
    data_3m = cursor.fetchall()
    cursor.execute(query_12m)
    data_12m = cursor.fetchall()
    cursor.close()
    return [data_3m, data_12m]

def fetch_staff_sales():
    query = """SELECT purchase_date 
               FROM purchases NATURAL JOIN ticket NATURAL JOIN flight WHERE airline_name="{}" ORDER BY purchase_date ASC""".format(session["airline"])
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    if not data:
        return False, False, False, False
    months = []
    now = datetime.datetime.today().year*100 + datetime.datetime.today().month
    t = data[0]["purchase_date"].year*100 + data[0]["purchase_date"].month
    months.append(t)
    while t < now:
        if t % 100 == 12:
            t += 88
        t += 1
        months.append(t)
    spendings = [0 for _ in range(len(months))]
    for row in data:
        month = row["purchase_date"].year*100 + row["purchase_date"].month
        m = months.index(month)
        spendings[m] += 1
    now = str(datetime.datetime.today().year) + "-" + str(datetime.datetime.today().month)
    past_year = datetime.datetime.today().year
    past_month = datetime.datetime.today().month - 6
    if past_month < 1:
        past_month += 12
        past_year -= 1
    past6m = str(past_year) + "-" + str(past_month)
    if len(now) < 7:
        now = now[:5] + "0" + now[-1]
    if len(past6m) < 7:
        past6m = past6m[:5] + "0" + past6m[-1]
    return months, spendings, now, past6m

def fetch_staff_breakdown():
    airline = session["airline"]
    query = """SELECT SUM(price)
            FROM flight NATURAL JOIN ticket NATURAL JOIN purchases
            WHERE airline_name = "{}" AND {} AND purchase_date > "{}" """
    direct = "booking_agent_id IS NULL"
    indirect = "booking_agent_id"
    query_direct1m = query.format(airline, direct, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_indirect1m = query.format(airline, indirect, str(datetime.datetime.today()-datetime.timedelta(days=30))[:-7])
    query_direct12m = query.format(airline, direct, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    query_indirect12m = query.format(airline, indirect, str(datetime.datetime.today()-datetime.timedelta(days=365))[:-7])
    cursor = conn.cursor()
    cursor.execute(query_direct1m)
    query_direct1m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_indirect1m)
    query_indirect1m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_direct12m)
    query_direct12m = cursor.fetchall()[0]["SUM(price)"]
    cursor.execute(query_indirect12m)
    query_indirect12m = cursor.fetchall()[0]["SUM(price)"]
    cursor.close()
    out = [query_indirect1m, query_direct1m, query_indirect12m, query_direct12m]
    for i in range(len(out)):
        try:
            out[i] = int(out[i])
        except:
            out[i] = 0
    return out

# The Main Thing ##################################################################################
# Initialise flask
app = Flask(__name__)
app.secret_key = pw2md5(str(random.random()))

# Configure pymysql
conn = pymysql.connect(host='localhost',
                       user='root',
                       password='',
                       db='air',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


# Home Page
@app.route("/")
def home():
    return render_template("home.html")

# Public Info
@app.route("/public_info", methods=['GET', 'POST'])
def public_info():
    # Display all public flight information
    query = "SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status FROM flight ORDER BY departure_time DESC"
    cursor = conn.cursor()
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template("public_info.html", data = data)

# Public Search
@app.route("/public_search", methods=['GET', 'POST'])
def public_search():
    # Search by the given requirements
    text = request.form["text"]
    method = request.form["method"]
    cursor = conn.cursor()
    query = "SELECT {} FROM {} WHERE {} = %s ORDER BY departure_time DESC"
    if method == "departure_airport" or method == "arrival_airport":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status", "flight", method)
        cursor.execute(query, (text))
    elif method == "departure_city":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status",
                             "flight, airport",
                             "departure_airport = airport_name and airport_city")
        cursor.execute(query, (text))
    elif method == "arrival_city":
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status",
                             "flight, airport",
                             "arrival_airport = airport_name and airport_city")
        cursor.execute(query, (text))
    elif method == "status":
        text = text[0].upper() + text[1:].lower()
        query = query.format("airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status", "flight", method)
        cursor.execute(query, (text))
    else:
        date_start = text + " 00:00:00"
        date_end = request.form["text2"] + " 23:59:59"
        query = "SELECT airline_name, flight_num, departure_airport, departure_time, arrival_airport, arrival_time, price, status FROM flight WHERE {} >= '{}' AND {} <= '{}' ORDER BY departure_time DESC"
        query = query.format(method, date_start, method, date_end)
        cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return render_template("public_info.html", data = data)

# Customer ############################################################################################
# Customer Sign Up
@app.route("/customer_signup", methods=['GET', 'POST'])
def customer_signup():
    return render_template("customer_signup.html", email_taken = False, saved_val = [None for _ in range(12)])

@app.route("/customer_signup_go", methods=['GET', 'POST'])
def customer_signup_go():
    # Check whether the email is taken
    email = request.form["email"]
    query = "SELECT * FROM customer WHERE email = %s"
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    if data:
        return render_template("customer_signup.html", email_taken = email, saved_val = [request.form["email"], request.form["name"], request.form["password"], 
            request.form["building_number"], request.form["street"], request.form["city"], request.form["state"], request.form["phone_number"], request.form["passport_number"], 
            request.form["passport_expiration"], request.form["passport_country"], request.form["date_of_birth"]])
    # Insert
    else:
        query = "INSERT INTO customer VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        cursor = conn.cursor()
        cursor.execute(query, (request.form["email"], request.form["name"], pw2md5(request.form["password"]), 
            request.form["building_number"], request.form["street"], request.form["city"], request.form["state"], request.form["phone_number"], request.form["passport_number"], 
            request.form["passport_expiration"], request.form["passport_country"], request.form["date_of_birth"]))
        cursor.close()
        conn.commit()
        return render_template("customer_login.html", email_taken = email, login_fail = False)

# Customer Log In
@app.route("/customer_login", methods=['GET', 'POST'])
def customer_login():
    return render_template("customer_login.html", email_taken = False, login_fail = False)

@app.route("/customer_login_go", methods=['GET', 'POST'])
def customer_login_go():
    email = request.form["email"]
    password = pw2md5(request.form["password"])
    query = "SELECT name FROM customer WHERE (email, password) = (%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (email, password))
    data = cursor.fetchall()
    cursor.close()
    if data:
        session["email"] = email
        session["class"] = "customer"
        session["name"] = data[0]["name"]
        months, spendings, now, past6m = fetch_customer_spending()
        return render_template("customer_home.html", greet = greet_customer(), data = fetch_customer_upcoming(), months = months, spendings = spendings, now = now, past6m = past6m)
    return render_template("customer_login.html", email_taken = False, login_fail = True)

# Customer Home
@app.route("/customer_home", methods=['GET', 'POST'])
def customer_home():
    if authorise_customer() == True:
        months, spendings, now, past6m = fetch_customer_spending()
        return render_template("customer_home.html", greet = greet_customer(), data = fetch_customer_upcoming(), months = months, spendings = spendings, now = now, past6m = past6m)
    return render_template("home.html")

# Customer Log out
@app.route("/customer_logout", methods=['GET', 'POST'])
def customer_logout():
    try:
        session.pop("email")
        session.pop("class")
        session.pop("name")
    except:
        pass
    return render_template("home.html")

# Customer View My Flights (default view)
@app.route("/customer_myflights", methods=['GET', 'POST'])
def customer_myflights():
    if authorise_customer() == True:
        return render_template("customer_myflights.html", data = fetch_customer_all())
    return render_template("home.html")

# Customer View My Flights (search)
@app.route("/customer_myflights_search", methods=['GET', 'POST'])
def customer_myflights_search():
    if authorise_customer() == True:
        email = session["email"]
        cursor = conn.cursor()

        # 获取表单数据
        departure_text = request.form.get("departure_text")
        arrival_text = request.form.get("arrival_text")
        departure_method = request.form.get("departure_method")
        arrival_method = request.form.get("arrival_method")
        
        method = request.form.get("method")
        text = request.form.get("text")
        text2 = request.form.get("text2")

        # 如果用户提供了departure_text和arrival_text，则执行地点搜索
        if departure_text and arrival_text and departure_method and arrival_method:
            # 基础查询语句包含airport表，用于根据机场名关联城市
            base_query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                                   f.arrival_airport, f.arrival_time, f.price, f.status, t.ticket_id, p.purchase_date
                            FROM purchases p 
                            NATURAL JOIN ticket t 
                            JOIN flight f ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                            JOIN airport a_dep ON f.departure_airport = a_dep.airport_name
                            JOIN airport a_arr ON f.arrival_airport = a_arr.airport_name
                            WHERE p.customer_email = %s """
            params = [email]

            # 根据用户选择的方式添加查询条件
            # departure_city：a_dep.airport_city = departure_text
            # departure_airport：f.departure_airport = departure_text
            if departure_method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(departure_text)
            elif departure_method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(departure_text)

            # arrival_city：a_arr.airport_city = arrival_text
            # arrival_airport：f.arrival_airport = arrival_text
            if arrival_method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(arrival_text)
            elif arrival_method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(arrival_text)

            base_query += " ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
        
        # 否则，如果method指示为日期搜索相关
        elif method in ["departure_time", "arrival_time", "purchase_date"] and text and text2:
            # 将日期补全小时、分、秒
            date_start = text + " 00:00:00"
            date_end = text2 + " 23:59:59"
            query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                              f.arrival_airport, f.arrival_time, f.price, f.status, t.ticket_id, p.purchase_date
                       FROM purchases p
                       NATURAL JOIN ticket t
                       JOIN flight f ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                       WHERE {} >= %s AND {} <= %s AND p.customer_email = %s
                       ORDER BY f.departure_time DESC""".format(method, method)
            cursor.execute(query, (date_start, date_end, email))
        
        else:
            # 若既没有地点搜索参数又没有日期搜索参数，返回所有记录或返回空
            # 根据需求决定，这里为简单返回空结果
            data = []
            cursor.close()
            return render_template("customer_myflights.html", data=data)

        data = cursor.fetchall()
        cursor.close()
        return render_template("customer_myflights.html", data=data)
    return render_template("home.html")


# Customer Search for Flights / Purchase Tickets
@app.route("/customer_availableflights", methods=['GET', 'POST'])
def customer_availableflights():
    if authorise_customer() == True:
        return render_template("customer_availableflights.html", data = fetch_customer_available())
    return render_template("home.html")

@app.route("/customer_availableflights_search", methods=['GET', 'POST'])
def customer_availableflights_search():
    if authorise_customer():
        cursor = conn.cursor()

        # 获取表单数据
        departure_text = request.form.get("departure_text")
        arrival_text = request.form.get("arrival_text")
        departure_method = request.form.get("departure_method")
        arrival_method = request.form.get("arrival_method")

        method = request.form.get("method")
        text = request.form.get("text")
        text2 = request.form.get("text2")

        # 与agent相同的基础查询
        base_query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                               f.arrival_airport, f.arrival_time, f.price, ap.seats, 
                               ap.seats - COUNT(t.ticket_id) AS available_seats
                        FROM flight f
                        NATURAL JOIN airplane ap
                        LEFT JOIN ticket t ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                        JOIN airport a_dep ON f.departure_airport = a_dep.airport_name
                        JOIN airport a_arr ON f.arrival_airport = a_arr.airport_name
                        WHERE f.status = "Upcoming" """
        
        params = []
        data = []

        # 地点搜索
        if departure_text and arrival_text and departure_method and arrival_method:
            if departure_method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(departure_text)
            elif departure_method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(departure_text)

            if arrival_method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(arrival_text)
            elif arrival_method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(arrival_text)

            base_query += " GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        # 时间范围搜索
        elif method in ["departure_time", "arrival_time"] and text and text2:
            date_start = text + " 00:00:00"
            date_end = text2 + " 23:59:59"
            query = base_query + " AND f.{} >= %s AND f.{} <= %s GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            query = query.format(method, method)
            cursor.execute(query, (date_start, date_end))
            data = cursor.fetchall()

        # 其他字段搜索（如status）
        elif method in ["departure_airport", "arrival_airport", "departure_city", "arrival_city", "status"]:
            if method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(text)
            elif method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(text)
            elif method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(text)
            elif method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(text)
            elif method == "status":
                text = text[0].upper() + text[1:].lower()
                base_query += " AND f.status = %s"
                params.append(text)

            base_query += " GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        else:
            # 无匹配条件则返回空结果
            data = []

        cursor.close()
        for row in data:
            for key in row.keys():
                row[key] = str(row[key])
        return render_template("customer_availableflights.html", data=data)
    return render_template("home.html")
@app.route("/customer_availableflights_purchase", methods=['GET', 'POST'])
def customer_availableflights_purchase():
    if authorise_customer() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        return render_template("customer_availableflights_purchase.html", data = data, error = False)
    return render_template("home.html")

@app.route("/customer_availableflights_purchase_go", methods=['GET', 'POST'])
def customer_availableflights_purchase_go():
    try:
        assert authorise_customer()
        data = request.form["data"]
        data = data.replace('\'','\"')
        data = json.loads(data)
        quant = request.form["quantity"]
        email = session["email"]
        for _ in range(int(quant)):
            query = "SELECT MAX(ticket_id) AS max_id FROM ticket"
            cursor = conn.cursor()
            cursor.execute(query)
            try:
                new_id = int(cursor.fetchall()[0]["max_id"]) + 1
            except:
                 new_id = 0
            query = """SELECT * FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = "Upcoming" AND (airline_name, flight_num) = (%s, %s) GROUP BY airline_name, flight_num HAVING seats > count(ticket_id)"""
            cursor.execute(query, (data["airline_name"], data["flight_num"]))
            assert(cursor.fetchall())
            query = "INSERT INTO ticket VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, data["airline_name"], data["flight_num"]))
            query = "INSERT INTO purchases(ticket_id, customer_email, purchase_date) VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, email, datetime.datetime.today()))
            cursor.close()
        conn.commit()
        return render_template("customer_availableflights_purchase_thankyou.html")
    except:
       return render_template("customer_availableflights_purchase.html", data = [data], error = True)

# Agent ###################################################################################################################
# Booking Agent Sign Up
@app.route("/agent_signup", methods=['GET', 'POST'])
def agent_signup():
    return render_template("agent_signup.html", email_taken = False, saved_val = [None for _ in range(2)])

@app.route("/agent_signup_go", methods=['GET', 'POST'])
def agent_signup_go():
    # Check whether the email is taken
    email = request.form["email"]
    password = pw2md5(request.form["password"])
    query = "SELECT * FROM booking_agent WHERE email = %s"
    cursor = conn.cursor()
    cursor.execute(query, (email))
    data = cursor.fetchall()
    cursor.close()
    if data:
        return render_template("agent_signup.html", email_taken = email, saved_val = [request.form["email"], request.form["password"]])
    # Insert
    else:
        query = "SELECT MAX(booking_agent_id) AS max_id FROM booking_agent"
        cursor = conn.cursor()
        cursor.execute(query)
        new_id = int(cursor.fetchall()[0]["max_id"]) + 1
        query = "INSERT INTO booking_agent VALUES (%s, %s, %s)"
        cursor.execute(query,(email, password, new_id))
        cursor.close()
        conn.commit()
        return render_template("agent_login.html", email_taken = email, login_fail = False)

# Booking Agent Login
@app.route("/agent_login", methods=['GET', 'POST'])
def agent_login():
    return render_template("agent_login.html", email_taken = False, login_fail = False)

@app.route("/agent_login_go", methods=['GET', 'POST'])
def agent_login_go():
    email = request.form["email"]
    password = pw2md5(request.form["password"])
    query = "SELECT booking_agent_id AS id FROM booking_agent WHERE (email, password) = (%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (email, password))
    data = cursor.fetchall()
    cursor.close()
    if data:
        session["email"] = email
        session["class"] = "agent"
        session["book_id"] = data[0]["id"]
        commission_data, now, past30d = fetch_agent_commission()
        return render_template("agent_home.html", data=fetch_agent_upcoming(), greet=greet_agent(), commission_data=commission_data, now=now, past30d = past30d)
    return render_template("agent_login.html", email_taken = False, login_fail = True)

# Agent Home
@app.route("/agent_home", methods=['GET', 'POST'])
def agent_home():
    if authorise_agent() == True:
        commission_data, now, past30d = fetch_agent_commission()
        return render_template("agent_home.html", data=fetch_agent_upcoming(), greet=greet_agent(), commission_data=commission_data, now=now, past30d = past30d)
    return render_template("home.html")

# Agent Log Out
@app.route("/agent_logout", methods=['GET', 'POST'])
def agent_logout():
    try:
        session.pop("email")
        session.pop("class")
        session.pop("book_id")
    except:
        pass
    return render_template("home.html")

# Agent View My Flights (default view)
@app.route("/agent_myflights", methods=['GET', 'POST'])
def agent_myflights():
    if authorise_agent() == True:
        return render_template("agent_myflights.html", data = fetch_agent_all())
    return render_template("home.html")

# Agent View My Flights (search)
@app.route("/agent_myflights_search", methods=['GET', 'POST'])
def agent_myflights_search():
    if authorise_agent():
        book_id = session["book_id"]
        cursor = conn.cursor()

        # 获取表单数据
        departure_text = request.form.get("departure_text")
        arrival_text = request.form.get("arrival_text")
        departure_method = request.form.get("departure_method")
        arrival_method = request.form.get("arrival_method")

        method = request.form.get("method")
        text = request.form.get("text")
        text2 = request.form.get("text2")

        # 基础查询语句（包含airport以便匹配城市）
        base_query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                               f.arrival_airport, f.arrival_time, f.price, f.status, t.ticket_id, p.purchase_date, p.customer_email
                        FROM purchases p
                        NATURAL JOIN ticket t
                        JOIN flight f ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                        JOIN airport a_dep ON f.departure_airport = a_dep.airport_name
                        JOIN airport a_arr ON f.arrival_airport = a_arr.airport_name
                        WHERE p.booking_agent_id = %s """

        params = [book_id]
        data = []

        # 优先判断是否是地点搜索（若departure_text和arrival_text都存在）
        if departure_text and arrival_text and departure_method and arrival_method:
            # 根据departure_method
            if departure_method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(departure_text)
            elif departure_method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(departure_text)

            # 根据arrival_method
            if arrival_method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(arrival_text)
            elif arrival_method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(arrival_text)

            base_query += " ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        # 若不是地点搜索则检查method是否是日期搜索
        elif method in ["departure_time", "arrival_time", "purchase_date"] and text and text2:
            # 日期搜索
            date_start = text + " 00:00:00"
            date_end = text2 + " 23:59:59"
            query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                              f.arrival_airport, f.arrival_time, f.price, f.status, t.ticket_id, p.purchase_date, p.customer_email
                       FROM purchases p
                       NATURAL JOIN ticket t
                       JOIN flight f ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                       WHERE p.booking_agent_id = %s AND {} >= %s AND {} <= %s
                       ORDER BY f.departure_time DESC""".format(method, method)
            cursor.execute(query, (book_id, date_start, date_end))
            data = cursor.fetchall()
        
        # 若为特定字段搜索（status, customer_email, 仅出发机场/抵达机场/城市）
        elif method in ["departure_airport", "arrival_airport", "status", "customer_email", "departure_city", "arrival_city"]:
            # 此处保持与之前逻辑相同，但需要在新的结构下适配
            # departure_city/arrival_city需要JOIN airport表
            # 已经在 base_query 中JOIN了airport, 所以使用base_query进行筛选
            if method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(text)
            elif method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(text)
            elif method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(text)
            elif method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(text)
            elif method == "status":
                # 格式化status
                text = text[0].upper() + text[1:].lower()
                base_query += " AND f.status = %s"
                params.append(text)
            elif method == "customer_email":
                base_query += " AND p.customer_email = %s"
                params.append(text)

            base_query += " ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        else:
            # 无匹配条件则返回空结果
            data = []

        cursor.close()
        return render_template("agent_myflights.html", data=data)
    return render_template("home.html")

# Agent Search for Flights / Purchase Tickets
@app.route("/agent_availableflights", methods=['GET', 'POST'])
def agent_availableflights():
    if authorise_agent() == True:
        return render_template("agent_availableflights.html", data = fetch_customer_available())
    return render_template("home.html")

@app.route("/agent_availableflights_search", methods=['GET', 'POST'])
def agent_availableflights_search():
    if authorise_agent():
        cursor = conn.cursor()

        # 获取表单数据
        departure_text = request.form.get("departure_text")
        arrival_text = request.form.get("arrival_text")
        departure_method = request.form.get("departure_method")
        arrival_method = request.form.get("arrival_method")

        method = request.form.get("method")
        text = request.form.get("text")
        text2 = request.form.get("text2")

        # 基础查询语句：flight、ticket、airplane已NATURAL JOIN
        # 在查询中增加JOIN airport，以便根据机场名称获取城市信息
        base_query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, 
                               f.arrival_airport, f.arrival_time, f.price, ap.seats, 
                               ap.seats - COUNT(t.ticket_id) AS available_seats
                        FROM flight f
                        NATURAL JOIN airplane ap
                        LEFT JOIN ticket t ON (t.airline_name = f.airline_name AND t.flight_num = f.flight_num)
                        JOIN airport a_dep ON f.departure_airport = a_dep.airport_name
                        JOIN airport a_arr ON f.arrival_airport = a_arr.airport_name
                        WHERE f.status = "Upcoming" """

        params = []
        data = []

        # 判断是否是地点搜索（若departure_text和arrival_text存在）
        if departure_text and arrival_text and departure_method and arrival_method:
            # 添加出发地条件
            if departure_method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(departure_text)
            elif departure_method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(departure_text)

            # 添加抵达地条件
            if arrival_method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(arrival_text)
            elif arrival_method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(arrival_text)

            base_query += " GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        # 如果是时间范围搜索
        elif method in ["departure_time", "arrival_time"] and text and text2:
            date_start = text + " 00:00:00"
            date_end = text2 + " 23:59:59"
            query = base_query + " AND f.{} >= %s AND f.{} <= %s GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            query = query.format(method, method)
            cursor.execute(query, (date_start, date_end))
            data = cursor.fetchall()

        # 其他字段搜索（如status, 仅出发机场/抵达机场/城市等）
        elif method in ["departure_airport", "arrival_airport", "departure_city", "arrival_city", "status"]:
            if method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(text)
            elif method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(text)
            elif method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(text)
            elif method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(text)
            elif method == "status":
                # 格式化status
                text = text[0].upper() + text[1:].lower()
                base_query += " AND f.status = %s"
                params.append(text)

            base_query += " GROUP BY f.airline_name, f.flight_num HAVING ap.seats > COUNT(t.ticket_id) ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        # 若为日期搜索(如purchase_date不存在于可用字段，这里仅示例保留)
        else:
            # 无匹配条件返回空结果
            data = []

        cursor.close()
        for row in data:
            for key in row.keys():
                row[key] = str(row[key])
        return render_template("agent_availableflights.html", data=data)
    return render_template("home.html")

@app.route("/agent_availableflights_purchase", methods=['GET', 'POST'])
def agent_availableflights_purchase():
    if authorise_agent() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        return render_template("agent_availableflights_purchase.html", data = data, error = False)
    return render_template("home.html")

@app.route("/agent_availableflights_purchase_go", methods=['GET', 'POST'])
def agent_availableflights_purchase_go():
    try:
        assert authorise_agent()
        book_id = session["book_id"]
        data = request.form["data"]
        data = data.replace('\'','\"')
        data = json.loads(data)
        quant = request.form["quantity"]
        email = request.form["customer_email"]
        for _ in range(int(quant)):
            query = "SELECT MAX(ticket_id) AS max_id FROM ticket"
            cursor = conn.cursor()
            cursor.execute(query)
            try:
                new_id = int(cursor.fetchall()[0]["max_id"]) + 1
            except:
                 new_id = 0
            query = """SELECT * FROM flight NATURAL JOIN ticket NATURAL JOIN airplane WHERE status = "Upcoming" AND (airline_name, flight_num) = (%s, %s) GROUP BY airline_name, flight_num HAVING seats > count(ticket_id)"""
            cursor.execute(query, (data["airline_name"], data["flight_num"]))
            assert(cursor.fetchall())
            query = "INSERT INTO ticket VALUES (%s, %s, %s)"
            cursor.execute(query, (new_id, data["airline_name"], data["flight_num"]))
            query = "INSERT INTO purchases VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (new_id, email, book_id, datetime.datetime.today()))
            cursor.close()
        conn.commit()
        return render_template("agent_availableflights_purchase_thankyou.html")
    except:
       return render_template("agent_availableflights_purchase.html", data = [data], error = True)

# Staff ####################################################################################################################
# Airline Staff Sign Up
@app.route("/staff_signup", methods=['GET', 'POST'])
def staff_signup():
    query = "SELECT airline_name FROM airline"
    cursor = conn.cursor()
    cursor.execute(query)
    airlines = cursor.fetchall()
    cursor.close()
    return render_template("staff_signup.html", email_taken=False, saved_val=[None for _ in range(6)], airlines=airlines)

@app.route("/staff_signup_go", methods=['GET', 'POST'])
def staff_signup_go():
    # Check whether the email (username) is taken
    username = request.form["username"]
    password = pw2md5(request.form["password"])
    query = "SELECT * FROM airline_staff WHERE username = %s"
    cursor = conn.cursor()
    cursor.execute(query, (username,))
    data = cursor.fetchall()
    cursor.close()
    if data:
        query = "SELECT airline_name FROM airline"
        cursor = conn.cursor()
        cursor.execute(query)
        airlines = cursor.fetchall()
        cursor.close()
        return render_template("staff_signup.html",
                               email_taken=username,
                               airlines=airlines,
                               saved_val=[request.form["username"], request.form["password"], request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]])
    else:
        # If new airline
        if request.form["airline"] == "new":
            query = "SELECT * FROM airline WHERE airline_name = %s"
            cursor = conn.cursor()
            cursor.execute(query, (request.form["new_airline"],))
            data = cursor.fetchall()
            cursor.close()
            if data:
                query = "SELECT airline_name FROM airline"
                cursor = conn.cursor()
                cursor.execute(query)
                airlines = cursor.fetchall()
                cursor.close()
                return render_template("staff_signup.html",
                                       email_taken=request.form["new_airline"],
                                       airlines=airlines,
                                       saved_val=[request.form["username"], request.form["password"], request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]])
            query = "INSERT INTO airline VALUES (%s)"
            cursor = conn.cursor()
            cursor.execute(query, (request.form["new_airline"],))
            cursor.close()
            conn.commit()

        query = "INSERT INTO airline_staff VALUES (%s, %s, %s, %s, %s, %s)"
        cursor = conn.cursor()
        cursor.execute(query, (username, password, request.form["first_name"], request.form["last_name"], request.form["date_of_birth"], request.form["airline"]))
        cursor.close()
        conn.commit()

        # 新注册的staff自动插入permission表，并设置权限为staff
        query = "INSERT INTO permission (username, permission_type) VALUES (%s, %s)"
        cursor = conn.cursor()
        cursor.execute(query, (username, 'staff'))
        cursor.close()
        conn.commit()

        return render_template("staff_login.html", email_taken=username, login_fail=False)
# Staff Login
@app.route("/staff_login", methods=['GET', 'POST'])
def staff_login():
    return render_template("staff_login.html", email_taken = False, login_fail = False)

@app.route("/staff_login_go", methods=['GET', 'POST'])
def staff_login_go():
    username = request.form["username"]
    password = pw2md5(request.form["password"])
    query = "SELECT * FROM airline_staff WHERE (username, password) = (%s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (username, password))
    data = cursor.fetchall()
    cursor.close()

    if data:
        # 获取permission_type
        query = "SELECT permission_type FROM permission WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        perm_data = cursor.fetchone()
        cursor.close()

        permission_type = None
        if perm_data:
            permission_type = perm_data["permission_type"]

        session["username"] = username
        session["class"] = "staff"
        session["airline"] = data[0]["airline_name"]
        com_data, nsales_data_month, nsales_data_year = fetch_staff_agent()
        months, sales, now, past6m = fetch_staff_sales()

        return render_template(
            "staff_home.html",
            data=fetch_staff_upcoming(),
            com_data=com_data,
            nsales_data_month=nsales_data_month,
            nsales_data_year=nsales_data_year,
            customer_data=fetch_staff_customer(),
            destination_data=fetch_staff_destination(),
            months=months,
            spendings=sales,
            now=now,
            past6m=past6m,
            breakdown=fetch_staff_breakdown(),
            permission_type=permission_type  # 将权限类型传入模板
        )
    return render_template("staff_login.html", email_taken=False, login_fail=True)
# Staff Home
@app.route("/staff_home", methods=['GET', 'POST'])
def staff_home():
    if authorise_staff() == True:
        com_data, nsales_data_month, nsales_data_year = fetch_staff_agent()
        months, sales, now, past6m = fetch_staff_sales()
        username = session.get("username")
        query = "SELECT permission_type FROM permission WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        perm_data = cursor.fetchone()
        cursor.close()
        
        if perm_data:
            permission_type = perm_data['permission_type']
        else:
            permission_type = 'staff'  # 默认权限
        
        return render_template("staff_home.html", data=fetch_staff_upcoming(), com_data=com_data, nsales_data_month=nsales_data_month, nsales_data_year=nsales_data_year, customer_data=fetch_staff_customer(), destination_data=fetch_staff_destination(),months=months, spendings=sales, now=now, past6m=past6m, breakdown=fetch_staff_breakdown(),permission_type=permission_type,)
    return render_template("home.html")

# Staff Log out
@app.route("/staff_logout", methods=['GET', 'POST'])
def staff_logout():
    try:
        session.pop("username")
        session.pop("class")
        session.pop("airline")
    except:
        pass
    return render_template("home.html")

# Staff View My Flights (default view)
@app.route("/staff_myflights", methods=['GET', 'POST'])
def staff_myflights():
    if authorise_staff() == True:
        # 获取当前登录的staff所属的airline
        airline = session["airline"]
        # 修改fetch_staff_all函数以接受airline参数，过滤相应航班
        data = fetch_staff_all(airline)  
        return render_template("staff_myflights.html", data = data)
    return render_template("home.html")


# Staff View My Flights (search)
@app.route("/staff_myflights_search", methods=['GET', 'POST'])
def staff_myflights_search():
    if authorise_staff():
        airline = session["airline"]
        cursor = conn.cursor()

        # 获取表单数据
        departure_text = request.form.get("departure_text")
        arrival_text = request.form.get("arrival_text")
        departure_method = request.form.get("departure_method")
        arrival_method = request.form.get("arrival_method")

        method = request.form.get("method")
        text = request.form.get("text")
        text2 = request.form.get("text2")

        # 基础查询语句：限制为当前staff所属的airline
        base_query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time, 
                               f.price, f.status, f.airplane_id
                        FROM flight f 
                        JOIN airport a_dep ON f.departure_airport = a_dep.airport_name
                        JOIN airport a_arr ON f.arrival_airport = a_arr.airport_name
                        WHERE f.airline_name = %s """
        params = [airline]
        data = []

        # 地点搜索
        if departure_text and arrival_text and departure_method and arrival_method:
            if departure_method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(departure_text)
            elif departure_method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(departure_text)

            if arrival_method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(arrival_text)
            elif arrival_method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(arrival_text)

            base_query += " ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        # 日期搜索
        elif method in ["departure_time", "arrival_time"] and text and text2:
            date_start = text + " 00:00:00"
            date_end = text2 + " 23:59:59"
            query = """SELECT f.airline_name, f.flight_num, f.departure_airport, f.departure_time, f.arrival_airport, f.arrival_time, 
                              f.price, f.status, f.airplane_id
                       FROM flight f
                       WHERE f.airline_name = %s AND {} >= %s AND {} <= %s
                       ORDER BY f.departure_time DESC""".format(method, method)
            cursor.execute(query, (airline, date_start, date_end))
            data = cursor.fetchall()

        # 其它特定字段搜索
        elif method in ["departure_airport", "arrival_airport", "departure_city", "arrival_city", "airplane_id", "status"]:
            if method == "departure_airport":
                base_query += " AND f.departure_airport = %s"
                params.append(text)
            elif method == "arrival_airport":
                base_query += " AND f.arrival_airport = %s"
                params.append(text)
            elif method == "departure_city":
                base_query += " AND a_dep.airport_city = %s"
                params.append(text)
            elif method == "arrival_city":
                base_query += " AND a_arr.airport_city = %s"
                params.append(text)
            elif method == "airplane_id":
                base_query += " AND f.airplane_id = %s"
                params.append(text)
            elif method == "status":
                # 格式化status
                text = text[0].upper() + text[1:].lower()
                base_query += " AND f.status = %s"
                params.append(text)

            base_query += " ORDER BY f.departure_time DESC"
            cursor.execute(base_query, tuple(params))
            data = cursor.fetchall()

        else:
            # 无匹配结果则返回空数据
            data = []

        cursor.close()

        # 将数据值转化为字符串（如有需要）
        for row in data:
            for key in row.keys():
                row[key] = str(row[key])

        return render_template("staff_myflights.html", data=data)
    return render_template("home.html")

# Staff View My Flights (view customer details)
@app.route("/staff_myflights_viewcustomers", methods=['GET', 'POST'])
def staff_myflights_viewcustomers():
    if authorise_staff() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        flight_num = data[0]["flight_num"]
        airline = session["airline"]
        query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                   WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email ORDER BY ticket_id"""
        cursor = conn.cursor()
        cursor.execute(query, (airline, flight_num))
        customer_data = cursor.fetchall()
        cursor.close()
        return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data)
    return render_template("home.html")

@app.route("/staff_myflights_viewcustomers_changestatus", methods=['GET', 'POST'])
def staff_myflights_viewcustomers_changestatus():
    if authorise_staff() == True:
        data = request.form["data"][1:-1]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        flight_num = data[0]["flight_num"]
        airline = session["airline"]
        status = request.form['status']
        try:
            assert(data[0]['status'] != status)
            cursor = conn.cursor()
            query = """UPDATE flight SET status = %s WHERE airline_name="{}" AND flight_num={} """.format(airline, flight_num)
            cursor.execute(query, (status))
            cursor.close()
            conn.commit()
            cursor = conn.cursor()
            query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                    WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email ORDER BY ticket_id"""
            cursor.execute(query, (airline, flight_num))
            customer_data = cursor.fetchall()
            query = """SELECT * FROM flight WHERE (airline_name, flight_num) = (%s, %s)"""
            cursor.execute(query, (airline, flight_num))
            data = cursor.fetchall()
            cursor.close()
            for row in data:
                for key in row.keys():
                    row[key] = str(row[key])
            return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data, success=True, error=False)
        except:
            cursor = conn.cursor()
            query = """SELECT email, name, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases, customer
                    WHERE customer.email = purchases.customer_email AND (airline_name, flight_num) = (%s, %s) GROUP BY email ORDER BY ticket_id"""
            cursor.execute(query, (airline, flight_num))
            customer_data = cursor.fetchall()
            cursor.close()
            return render_template("staff_myflights_viewcustomers.html", data=data, customer_data=customer_data, error=True, success=False)
    return render_template("home.html")

# Staff Add Flight
@app.route("/staff_addflight", methods=['GET', 'POST'])
def staff_addflight():
    if authorise_staff() == True:
        username = session.get("username")
        
        # 检查此staff是否具备admin权限
        query = "SELECT permission_type FROM permission WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        perm_data = cursor.fetchone()
        cursor.close()

        # 如果不存在记录或权限类型不是admin，则无权限添加航班
        if not perm_data or perm_data['permission_type'] != 'Admin':
            return render_template("home.html", error="You do not have permission to add flights.")

        airline = session["airline"]
        query = "SELECT DISTINCT airport_name FROM airport"
        cursor = conn.cursor()
        cursor.execute(query)
        airports = cursor.fetchall()

        query = "SELECT DISTINCT airplane_id FROM airplane WHERE airline_name = %s"
        cursor.execute(query, (airline,))
        airplane_ids = cursor.fetchall()

        query = "SELECT MAX(flight_num) as max_fnum FROM flight WHERE airline_name = %s"
        cursor.execute(query, (airline,))
        flight_num = cursor.fetchall()
        cursor.close()

        for i in flight_num[0].keys():
            flight_num[0][i] = int(flight_num[0][i]) + 1

        return render_template("staff_addflight.html", airline=session["airline"], airports=airports, airplane_ids=airplane_ids, flight_num=flight_num)
    return render_template("home.html")

@app.route("/staff_addflight_go", methods=['GET', 'POST'])
def staff_addflight_go():
    if authorise_staff() == True:
        try:
            assert request.form["arrival_airport"] != request.form["departure_airport"]
            airline = session["airline"]
            start = request.form["departure_time"]
            end = request.form["arrival_time"]
            start = start[:-6] + " " + start[-5:] + ":00"
            end = end[:-6] + " " + end[-5:] + ":00"
            # Check for time conflicts
            query = """SELECT * FROM flight WHERE (airline_name = "{}" AND airplane_id = {} AND ((departure_time > '{}' AND departure_time < '{}') 
                    OR (arrival_time > '{}' AND arrival_time < '{}')
                    OR (departure_time < '{}' AND arrival_time > '{}')))
                    OR '{}' >= '{}'""".format(airline, request.form['plane_id'], start, end, start, end, start, end, start, end)
            cursor = conn.cursor()
            print(query)
            cursor.execute(query)
            data = cursor.fetchall()
            assert data == ()
            # Insert
            query = """INSERT INTO flight VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(query, (airline, request.form["flight_num"], request.form["departure_airport"], start, request.form["arrival_airport"], 
                end, request.form["price"], request.form["status"], request.form["plane_id"]))
            cursor.close()
            conn.commit()
            error = False
            success = True
        except:
            error = True
            success = False
        
        airline = session["airline"]
        query = "SELECT DISTINCT airport_name FROM airport"
        cursor = conn.cursor()
        cursor.execute(query)
        airports = cursor.fetchall()
        query = "SELECT DISTINCT airplane_id FROM airplane WHERE airline_name = %s"
        cursor.execute(query, (airline))
        airplane_ids = cursor.fetchall()
        query = "SELECT MAX(flight_num) FROM flight WHERE airline_name = %s"
        cursor.execute(query, (airline))
        flight_num = cursor.fetchall()
        cursor.close()
        for i in flight_num[0].keys():
            flight_num[0][i] = int(flight_num[0][i]) + 1
        return render_template("staff_addflight.html", airline=session["airline"], airports=airports, airplane_ids=airplane_ids, flight_num=flight_num, error=error, success=success)
    return render_template("home.html")

# Staff Add Plane
@app.route("/staff_addplane", methods=['GET', 'POST'])
def staff_addplane():
    if authorise_staff():
        username = session.get("username")
        
        # 检查权限
        query = "SELECT permission_type FROM permission WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        perm_data = cursor.fetchone()

        # 没有admin权限，不允许添加飞机
        if not perm_data or perm_data['permission_type'] != 'Admin':
            cursor.close()
            return render_template("home.html", error="You do not have permission to add airplanes.")

        query = """SELECT MAX(airplane_id) AS MAX_id FROM airplane WHERE airline_name = %s"""
        cursor.execute(query, (session["airline"],))
        try:
            plane_id = int(cursor.fetchall()[0]['MAX_id']) + 1
        except:
            plane_id = 0
        cursor.close()
        return render_template("staff_addplane.html", airline=session["airline"], plane_id=plane_id)
    return render_template("home.html")


@app.route("/staff_addplane_go", methods=['GET', 'POST'])
def staff_addplane_go():
    if authorise_staff() == True:
        try:
            airline = session["airline"]
            query = "INSERT INTO airplane VALUES (%s, %s, %s)"
            cursor = conn.cursor()
            cursor.execute(query, (airline, request.form["plane_id"], request.form["seats"]))
            cursor.close()
            conn.commit()
            query = """SELECT * FROM airplane WHERE airline_name = %s"""
            cursor = conn.cursor()
            cursor.execute(query, (airline))
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_addplane_go.html", data=data)
        except:
            return render_template("staff_addplane.html", airline=session["airline"], plane_id=request.form["plane_id"], seats=request.form["seats"], error=True)
    return render_template("home.html")

# Staff Add Airport
@app.route("/staff_addairport", methods=['GET', 'POST'])
def staff_addairport():
    if authorise_staff() == True:
        query = """SELECT * FROM airport"""
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_addairport.html", data=data)
    return render_template("home.html")

@app.route("/staff_addairport_go", methods=['GET', 'POST'])
def staff_addairport_go():
    if authorise_staff() == True:
        try:
            query = """INSERT INTO airport VALUES (%s,%s)"""
            cursor = conn.cursor()
            cursor.execute(query, (request.form['airport'],request.form['city']))
            cursor.close()
            conn.commit()
            error = False
        except:
            error = True
        query = """SELECT * FROM airport"""
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_addairport.html", data=data, error=error)
    return render_template("home.html")

@app.route("/staff_home", methods=['GET', 'POST'])
def is_admin(username):
    try:
        conn = pymysql.connect(host="localhost", database="air", user="root", password="")
        try:
            with conn.cursor() as cursor:
                query = "SELECT permission_type FROM permission WHERE username = %s"
                cursor.execute(query, (username,))
                result = cursor.fetchone()
                if result:
                    perm_data = dict(zip([column[0] for column in cursor.description], result))
                    return perm_data["permission_type"] == "Admin"
                return False
        finally:
            conn.close()
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return False
@app.route("/staff_home", methods=['GET', 'POST'])
def get_staff_airline(username):
    conn = pymysql.connect(host='localhost', user='root', password='', database='air')
    try:
        with conn.cursor() as cursor:
            query = "SELECT airline_name FROM airline_staff WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()  # 获取单条查询结果
            if result:
                # 将结果 (tuple) 转换为字典
                desc = cursor.description  # 获取列描述信息
                column_names = [col[0] for col in desc]
                data = dict(zip(column_names, result))
                return data['airline_name']
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()  # 确保连接始终关闭
    return None
@app.route("/staff_home", methods=['GET', 'POST'])
def grant_new_permissions(admin_username, target_username, new_permission_type):
    # 检查admin权限和航空公司一致性
    if not is_admin(admin_username):
        return {"success": False, "error": "You do not have admin permission."}

    admin_airline = get_staff_airline(admin_username)
    target_airline = get_staff_airline(target_username)

    if not target_airline or admin_airline != target_airline:
        return {"success": False, "error": "Target staff not found or not in the same airline."}

    cursor = conn.cursor()
    query = "SELECT * FROM permission WHERE username = %s"
    cursor.execute(query, (target_username,))
    perm_data = cursor.fetchone()

    if perm_data:
        query = "UPDATE permission SET permission_type = %s WHERE username = %s"
        cursor.execute(query, (new_permission_type, target_username))
    else:
        query = "INSERT INTO permission (username, permission_type) VALUES (%s, %s)"
        cursor.execute(query, (target_username, new_permission_type))
    conn.commit()
    cursor.close()
    return {"success": True}


@app.route("/staff_grant_permission", methods=["POST"])
def grant_permission_route():
    if authorise_staff():  # 确保已登录staff
        admin_username = session.get("username")
        target_username = request.form.get("target_username")
        new_permission_type = request.form.get("new_permission_type")

        result = grant_new_permissions(admin_username, target_username, new_permission_type)
        if result["success"]:
            flash("Permission granted successfully.", "success")
        else:
            flash(result["error"], "error")
        return redirect("/staff_home")
    return render_template("home.html", error="Not authorised")


@app.route("/staff_add_booking_agent", methods=['GET', 'POST'])
def staff_add_booking_agent():
    if authorise_staff():
        username = session.get("username")
        
        # 检查权限
        query = "SELECT permission_type FROM permission WHERE username = %s"
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        perm_data = cursor.fetchone()
        permission_type = perm_data['permission_type']
        print(permission_type)

        # 没有admin权限，不允许添加代理
        if not perm_data or perm_data['permission_type'] != 'Admin':
            print("Please")
            cursor.close()
            return render_template("home.html", error="You do not have permission to add booking agents.")

        cursor.close()
        print("2nd")
        return render_template("staff_add_booking_agent.html", permission_type= perm_data['permission_type'])
    return render_template("home.html")

@app.route("/staff_add_booking_agent_go", methods=['GET','POST'])
def staff_add_booking_agent_go():
    if authorise_staff():
        print("1")
        try:
            # 从表单获取代理信息
            print("try1")
            agent_email = request.form["agent_email"]
            print("try2")
            query = "INSERT INTO booking_agent_work_for (email, airline_name) VALUES (%s, %s)"
            print("try3")
            cursor = conn.cursor()
            print(session["airline"])
            cursor.execute(query, (agent_email, session["airline"]))
            print("try4")
            cursor.close()
            conn.commit()
            # 显示更新后的代理列表
            query = "SELECT * FROM booking_agent"
            cursor = conn.cursor()
            print("try5")
            cursor.execute(query)
            data = cursor.fetchall()
            cursor.close()
            return render_template("staff_add_booking_agent.html", message = "You have successfully updated the agent info")
        except Exception as e:
            print("try6")
            return render_template("staff_add_booking_agent.html", error=True, message=str(e))
    return render_template("home.html")


# Staff View All Agents
@app.route("/staff_agents", methods=['GET', 'POST'])
def staff_agents():
    if authorise_staff() == True:
        query = """SELECT email, booking_agent.booking_agent_id, COUNT(price), SUM(price)*0.1 FROM flight NATURAL JOIN ticket NATURAL JOIN purchases RIGHT JOIN booking_agent ON purchases.booking_agent_id = booking_agent.booking_agent_id WHERE airline_name = "{}" GROUP BY booking_agent.booking_agent_id ORDER BY booking_agent.booking_agent_id """.format(session["airline"])
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_agents.html", data=data)
    return render_template("home.html")

# Staff View All Relavant Customers
@app.route("/staff_customers", methods=['GET', 'POST'])
def staff_customers():
    if authorise_staff() == True:
        airline = session["airline"]
        query = """SELECT email, name, COUNT(ticket_id)
                FROM flight NATURAL JOIN ticket NATURAL JOIN purchases JOIN customer ON customer.email = purchases.customer_email
                WHERE airline_name = "{}"
                GROUP BY email
                ORDER BY COUNT(ticket_id) DESC""".format(airline)
        cursor = conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        return render_template("staff_customers.html", data=data)
    return render_template("home.html")

# Staff View Customer Flight (Ticket) Details
@app.route("/staff_customers_details", methods=['GET', 'POST'])
def staff_customers_details():
    if authorise_staff() == True:
        data = request.form["data"]
        data = data.replace('{\'','{\"')
        data = data.replace('\'}','\"}')
        data = data.replace('\':','\":')
        data = data.replace('\',','\",')
        data = data.replace(' \'',' \"')
        data = [json.loads(data)]
        airline = session["airline"]
        customer = data[0]["email"]
        query = """SELECT flight_num, ticket_id FROM flight NATURAL JOIN ticket NATURAL JOIN purchases WHERE airline_name = "{}" AND customer_email = "{}" """.format(airline, customer)
        cursor = conn.cursor()
        cursor.execute(query)
        flight_data = cursor.fetchall()
        cursor.close()
        return render_template("staff_customers_details.html", data=data, flight_data=flight_data)
    return render_template("home.html")

if __name__ == "__main__":
    app.run(debug = True)