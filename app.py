from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pandas as pd
import os
import unicodedata
import re


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
merged_df = pd.read_csv('merged_data.csv', parse_dates=['ds'])

# ------------------------------------------------------------------------------------
# MODELOS DE BASE DE DATOS
# ------------------------------------------------------------------------------------
class RawSalesData(db.Model):
    """
    Almacena los datos crudos de VENTAS_TROCIUK3.csv (ventas reales).
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    cod_articulo = db.Column(db.String(50), nullable=False)
    product = db.Column(db.String(100), nullable=False)
    units_sold = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Integer, nullable=False)

class ForecastData(db.Model):
    """
    Almacena los datos de merged_data.csv (pronósticos).
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    product = db.Column(db.String(100), nullable=False)
    forecast_units = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=True)
    revenue = db.Column(db.Integer, nullable=True)

class MaterialData(db.Model):
    """
    Almacena los datos de materials.csv (materia prima inventada).
    """
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.String(50), nullable=False)
    material_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date_needed = db.Column(db.Date, nullable=False)
    quantity_kg = db.Column(db.Integer, nullable=False)
    cost_per_kg = db.Column(db.Integer, nullable=False)
    total_cost = db.Column(db.Integer, nullable=False)

# ------------------------------------------------------------------------------------
# FUNCIONES DE CARGA DE DATOS
# ------------------------------------------------------------------------------------
def load_raw_data(csv_path):
    """
    Lee VENTAS_TROCIUK3.csv, con formato de fecha dd/mm/yyyy,
    y devuelve registros para insertar en RawSalesData.
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] Archivo de datos crudos '{csv_path}' no encontrado.")
        return []

    df = pd.read_csv(csv_path, encoding="latin-1", on_bad_lines="skip")
    # Limpieza de columnas
    df.columns = df.columns.str.strip().str.replace('"', '', regex=False)
    df.columns = df.columns.str.replace('\ufeff', '', regex=False)
    df.columns = df.columns.str.replace('\r', '', regex=False)
    df.columns = df.columns.str.replace('\n', '', regex=False)
    df.columns = df.columns.str.replace('\u200b', '', regex=False)
    df.columns = df.columns.str.replace('\xa0', '', regex=False)
    df.columns = df.columns.str.replace(r'[^\x00-\x7F]+', '', regex=True)

    print("----- CSV Column Debug (Raw Data) -----")
    print("Detected columns after cleanup:", df.columns.tolist())
    print("----------------------------------------")

    required_cols = ['FECHA', 'COD_ARTICULO', 'DESCRIPCION', 'TOTAL_CANTIDAD', 'PRECIO_UNITARIO']
    if not all(col in df.columns for col in required_cols):
        print(f"[ERROR] Faltan columnas requeridas. Expected: {required_cols}")
        return []

    # Convert FECHA a datetime (dd/mm/yyyy)
    df['FECHA'] = pd.to_datetime(df['FECHA'], format='%d/%m/%Y', errors='coerce')

    records = []
    for _, row in df.iterrows():
        if pd.isnull(row['FECHA']) or pd.isnull(row['DESCRIPCION']):
            continue

        fecha = row['FECHA'].date()
        cod_art = str(row['COD_ARTICULO'])
        descr = str(row['DESCRIPCION'])
        units_sold = int(row['TOTAL_CANTIDAD'])
        price = int(row['PRECIO_UNITARIO'])
        revenue = units_sold * price

        record = RawSalesData(
            date=fecha,
            cod_articulo=cod_art,
            product=descr,
            units_sold=units_sold,
            price=price,
            revenue=revenue
        )
        records.append(record)

    return records

def load_forecast_data(csv_path):
    """
    Lee merged_data.csv y devuelve registros para ForecastData.
    Columnas esenciales: ds, yhat, PRODUCT
    - ds = fecha pronosticada
    - yhat = unidades pronosticadas
    - PRODUCT = producto
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] Archivo de pronóstico '{csv_path}' no encontrado.")
        return []

    df = pd.read_csv(csv_path, encoding="latin-1", on_bad_lines="skip")
    # Limpieza
    df.columns = df.columns.str.strip().str.replace('"', '', regex=False)
    df.columns = df.columns.str.replace('\ufeff', '', regex=False)
    df.columns = df.columns.str.replace(r'[^\x00-\x7F]+', '', regex=True)

    print("----- CSV Column Debug (Forecast) -----")
    print("Detected columns after cleanup:", df.columns.tolist())
    print("----------------------------------------")

    required_cols = ['ds', 'yhat', 'PRODUCT']
    if not all(col in df.columns for col in required_cols):
        print(f"[ERROR] Faltan columnas requeridas: {required_cols}")
        return []

    df['ds'] = pd.to_datetime(df['ds'], errors='coerce')

    # If there's a PRECIO_UNITARIO, rename to PRICE
    if 'PRECIO_UNITARIO' in df.columns:
        df.rename(columns={'PRECIO_UNITARIO': 'PRICE'}, inplace=True)
        print("[DEBUG] 'PRECIO_UNITARIO' column found and renamed to 'PRICE'.")
    if 'PRICE' not in df.columns:
        df['PRICE'] = 0

    records = []
    for _, row in df.iterrows():
        if pd.isnull(row['ds']) or pd.isnull(row['PRODUCT']):
            continue

        forecast_units = int(round(row['yhat']))
        price = int(round(row['PRICE']))
        revenue = forecast_units * price

        record = ForecastData(
            date=row['ds'].date(),
            product=str(row['PRODUCT']),
            forecast_units=forecast_units,
            price=price,
            revenue=revenue
        )
        records.append(record)

    return records

def load_material_data(csv_path):
    """
    Lee materials.csv y devuelve registros para MaterialData.
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] Archivo de materiales '{csv_path}' no encontrado.")
        return []

    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    df.columns = df.columns.str.strip().str.replace(r'[^\x00-\x7F]+', '', regex=True)

    print("----- CSV Column Debug (Materials) -----")
    print("Detected columns:", df.columns.tolist())
    print("----------------------------------------")

    required_cols = [
        'MaterialID', 'MaterialName', 'Category',
        'DateNeeded', 'QuantityKG', 'CostPerKG', 'TotalCost'
    ]
    if not all(col in df.columns for col in required_cols):
        print(f"[ERROR] Faltan columnas requeridas en materials.csv: {required_cols}")
        return []

    df['DateNeeded'] = pd.to_datetime(df['DateNeeded'], errors='coerce')

    records = []
    for _, row in df.iterrows():
        if pd.isnull(row['DateNeeded']) or pd.isnull(row['MaterialID']):
            continue

        record = MaterialData(
            material_id=str(row['MaterialID']),
            material_name=str(row['MaterialName']),
            category=str(row['Category']),
            date_needed=row['DateNeeded'].date(),
            quantity_kg=int(row['QuantityKG']),
            cost_per_kg=int(row['CostPerKG']),
            total_cost=int(row['TotalCost'])
        )
        records.append(record)
    return records

# ------------------------------------------------------------------------------------
# RUTAS PRINCIPALES
# ------------------------------------------------------------------------------------
@app.route('/')
def index():
    products = RawSalesData.query.with_entities(RawSalesData.product).distinct().all()
    product_list = [p[0] for p in products]
    print("[INFO] User visited / (Datos Crudos). Products found:", product_list)
    return render_template("index.html", animals=product_list)

@app.route('/forecasting')
def forecasting():
    """
    Muestra la página de pronósticos usando ForecastData (cargado desde merged_data.csv).
    """
    products = ForecastData.query.with_entities(ForecastData.product).distinct().all()
    product_list = ["All"] + [p[0] for p in products]

    default_limit = 10
    forecast_data = ForecastData.query.order_by(ForecastData.date).limit(default_limit).all()

    data_for_template = []
    for row in forecast_data:
        data_for_template.append({
            'date': row.date.strftime('%Y-%m-%d'),
            'Animal': row.product,
            'units_sold': row.forecast_units,
            'revenue': row.revenue
        })

    print("[INFO] User visited /forecasting. Distinct products:", product_list)
    return render_template("forecasting.html", data=data_for_template, animals=product_list)

@app.route('/materials')
def materials_page():
    print("[INFO] User visited /materials (Materias Primas).")
    return render_template("materials.html")

# ------------------------------------------------------------------------------------
# RUTAS DE API PARA DATOS CRUDOS
# ------------------------------------------------------------------------------------
@app.route('/data/<descripcion>', methods=['GET'])
def data_route(descripcion):
    limit = request.args.get('limit', default=10, type=int)
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)
    selected_year = request.args.get('year', default=None)

    query = RawSalesData.query

    if descripcion != "All":
        query = query.filter_by(product=descripcion)

    if selected_year and selected_year != "All":
        query = query.filter(db.extract('year', RawSalesData.date) == int(selected_year))
    else:
        if start_date:
            query = query.filter(RawSalesData.date >= start_date)
        if end_date:
            query = query.filter(RawSalesData.date <= end_date)

    rows = query.order_by(RawSalesData.date).limit(limit).all()

    data = [{
        "fecha": row.date.strftime("%Y-%m-%d"),
        "cod_articulo": row.cod_articulo,
        "descripcion": row.product,
        "total_cantidad": row.units_sold,
        "precio_unitario": row.price
    } for row in rows]

    return jsonify(data)


# ------------------------------------------------------------------------------------
# RUTAS DE API PARA DATOS DE PRONÓSTICO
# ------------------------------------------------------------------------------------
@app.route('/forecast_data/<product>', methods=['GET'])
def forecast_data_route(product):
    """
    Devuelve JSON de ForecastData (merged_data.csv).
    Soporta ?limit= & ?start_date= para filtrar pronóstico a partir de 2024, etc.
    """
    limit = request.args.get('limit', default=100, type=int)
    start_date_str = request.args.get('start_date', default='2024-01-01')

    try:
        start_date = datetime.fromisoformat(start_date_str)
    except ValueError:
        start_date = None

    query = ForecastData.query
    if start_date:
        query = query.filter(ForecastData.date >= start_date)
    if product != "All":
        query = query.filter(ForecastData.product == product)

    forecast_data = query.order_by(ForecastData.date).limit(limit).all()
    data = []
    for row in forecast_data:
        data.append({
            'date': row.date.strftime('%Y-%m-%d'),
            'product': row.product,
            'units_sold': row.forecast_units,
            'revenue': row.revenue
        })

    print(f"[INFO] JSON request for /forecast_data/{product}?limit={limit}&start_date={start_date_str}. Rows: {len(data)}")
    return jsonify(data)

# ------------------------------------------------------------------------------------
# RUTA DE API PARA DATOS DE MATERIALES
# ------------------------------------------------------------------------------------
@app.route('/materials_data', methods=['GET'])
def materials_data_route():
    limit = request.args.get('limit', default=1000, type=int)
    category_filter = request.args.get('category', default='All', type=str)
    min_stock = request.args.get('min_stock', default=0, type=int)

    query = MaterialData.query
    if category_filter != "All":
        query = query.filter(MaterialData.category == category_filter)
    if min_stock > 0:
        query = query.filter(MaterialData.quantity_kg >= min_stock)

    materials_data = query.order_by(MaterialData.material_id).limit(limit).all()
    data = []
    for row in materials_data:
        data.append({
            'id': row.material_id,
            'nombre': row.material_name,
            'categoria': row.category,
            'stock': row.quantity_kg,
            'cost': row.total_cost
        })

    print(f"[INFO] JSON request for /materials_data?category={category_filter}&min_stock={min_stock}&limit={limit}. Rows: {len(data)}")
    return jsonify(data)


# ------------------------------------------------------------------------------------
# COMANDOS FLASK PARA CARGAR DATOS
# ------------------------------------------------------------------------------------
@app.cli.command("load-data")
def load_data_command():
    """
    1) Borra registros antiguos de RawSalesData & ForecastData.
    2) Carga VENTAS_TROCIUK3.csv -> RawSalesData.
    3) Carga merged_data.csv -> ForecastData.
    4) Muestra conteos.
    """
    print("[INFO] Starting data load...")

    db.session.query(RawSalesData).delete()
    db.session.query(ForecastData).delete()
    db.session.commit()
    print("[INFO] Old data cleared from RawSalesData & ForecastData.")

    # Cargar VENTAS_TROCIUK3.csv (real data)
    raw_records = load_raw_data("VENTAS_TROCIUK3.csv")
    if raw_records:
        db.session.bulk_save_objects(raw_records)
        db.session.commit()
        print(f"[SUCCESS] Inserted {len(raw_records)} rows into RawSalesData.")
    else:
        print("[WARNING] No RawSalesData rows inserted.")

    # Cargar merged_data.csv (forecast)
    forecast_records = load_forecast_data("merged_data.csv")
    if forecast_records:
        db.session.bulk_save_objects(forecast_records)
        db.session.commit()
        print(f"[SUCCESS] Inserted {len(forecast_records)} rows into ForecastData.")
    else:
        print("[WARNING] No ForecastData rows inserted.")

    raw_count = RawSalesData.query.count()
    fore_count = ForecastData.query.count()
    print(f"[INFO] Final RawSalesData count: {raw_count}")
    print(f"[INFO] Final ForecastData count: {fore_count}")
    print("[INFO] load-data command finished.")

@app.cli.command("load-materials")
def load_materials_command():
    """
    1) Borra registros antiguos de MaterialData.
    2) Carga materials.csv.
    3) Muestra conteo.
    """
    print("[INFO] Starting material data load...")
    db.session.query(MaterialData).delete()
    db.session.commit()
    print("[INFO] Old data cleared from MaterialData.")

    material_records = load_material_data("materials.csv")
    if material_records:
        db.session.bulk_save_objects(material_records)
        db.session.commit()
        print(f"[SUCCESS] Inserted {len(material_records)} rows into MaterialData.")
    else:
        print("[WARNING] No MaterialData rows inserted.")

    mat_count = MaterialData.query.count()
    print(f"[INFO] Final MaterialData count: {mat_count}")
    print("[INFO] load-materials command finished.")



@app.route('/comparison')
def comparison():
    """
    Página de comparación entre datos reales y pronóstico.
    """
    # Lista de productos únicos desde merged_data.csv
    product_list = ["All"] + merged_df["PRODUCT"].unique().tolist()
    return render_template("comparison.html", forecast_products=product_list)

@app.route('/comparison_data', methods=['GET'])
def comparison_data():
    """
    Retorna JSON con campos: date, actual, forecast.
    """
    product_filter = request.args.get('product', 'All', type=str)
    start_date_str = request.args.get('start_date', '2024-01-01')
    end_date_str = request.args.get('end_date', '2025-12-31')

    # Manejar fechas
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    except ValueError:
        start_date = datetime(2024, 1, 1)

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        end_date = datetime(2025, 12, 31)

    # Filtrar el DataFrame
    filtered_df = merged_df[(merged_df['ds'] >= start_date) & (merged_df['ds'] <= end_date)]

    if product_filter != 'All':
        filtered_df = filtered_df[filtered_df['PRODUCT'] == product_filter]

    # Agrupar por fecha y sumar ventas y pronósticos
    grouped_df = filtered_df.groupby('ds').agg({
        'VENTAS_REALES': 'sum',
        'yhat': 'sum'
    }).reset_index()

    # Construir la respuesta JSON
    combined_data = []
    for _, row in grouped_df.iterrows():
        combined_data.append({
            "date": row['ds'].strftime('%Y-%m-%d'),
            "actual": row['VENTAS_REALES'],
            "forecast": row['yhat']
        })

    return jsonify(combined_data)

# ------------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    print("[INFO] Running app in debug mode on http://127.0.0.1:5000")
    app.run(debug=True)
