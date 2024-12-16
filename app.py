from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------------------------------------------------------------------------
# MODELOS DE BASE DE DATOS
# ------------------------------------------------------------------------------------

class SalesData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    animal = db.Column(db.String(50), nullable=False)
    units_sold = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Integer, nullable=False)

class MaterialNeeded(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False)
    material_name = db.Column(db.String(50), nullable=False)
    animal_food = db.Column(db.String(50), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'month': self.month,
            'material_name': self.material_name,
            'animal_food': self.animal_food,
            'quantity_needed': self.quantity_needed
        }

class MaterialSummary(db.Model):
    """
    Tabla resumen que agrupa los datos de MaterialNeeded por mes, animal y material.
    Almacena la suma total de quantity_needed.
    """
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False)
    material_name = db.Column(db.String(50), nullable=False)
    animal_food = db.Column(db.String(50), nullable=False)
    total_quantity = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'month': self.month,
            'material_name': self.material_name,
            'animal_food': self.animal_food,
            'total_quantity': self.total_quantity
        }

# ------------------------------------------------------------------------------------
# FUNCIONES DE CARGA DE DATOS
# ------------------------------------------------------------------------------------

def load_sales_data(csv_path):
    if not os.path.exists(csv_path):
        print(f"Archivo de datos de ventas '{csv_path}' no encontrado.")
        return []

    df = pd.read_csv(csv_path)
    required_columns = ['Date', 'Animal', 'Price (Miles de Guaranies)', 'Units Sold']
    if not all(col in df.columns for col in required_columns):
        print(f"Faltan columnas requeridas en el CSV de ventas. Columnas encontradas: {df.columns.tolist()}")
        return []

    df.rename(columns={
        'Date': 'date',
        'Animal': 'animal',
        'Price (Miles de Guaranies)': 'price',
        'Units Sold': 'units_sold'
    }, inplace=True)

    records = []
    for _, row in df.iterrows():
        try:
            date_val = datetime.strptime(row['date'], '%Y-%m-%d')
            record = SalesData(
                date=date_val,
                animal=row['animal'],
                units_sold=row['units_sold'],
                price=row['price'],
                revenue=row['units_sold'] * row['price']
            )
            records.append(record)
        except Exception as e:
            print(f"Error procesando la fila {row}: {e}")
    return records

# ------------------------------------------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS Y CARGA DE DATOS
# ------------------------------------------------------------------------------------

with app.app_context():
    db.create_all()

    # Cargar datos de ventas si no existen
    if SalesData.query.first() is None:
        sales_records = load_sales_data("Supermix_Sales_data.csv")
        if sales_records:
            db.session.bulk_save_objects(sales_records)
            db.session.commit()
            print("Datos de ventas cargados en la base de datos.")
        else:
            print("No se cargaron datos de ventas.")

    # Definir la materia prima necesaria por unidad para cada animal
    data_comida = {
        'Animal': ['Cow', 'Horses', 'Pig', 'Chicken'],
        'Trigo_g': [1, 0.8, 0.5, 0.2],
        'Suplemento_Vitaminico_g': [0.2, 0.14, 0.1, 0.05],
        'Heno_g': [3, 2, 1, 0.5],
        'Agua_g': [0.5, 0.6, 0.3, 0.2]
    }
    df_comida = pd.DataFrame(data_comida)

    # Cargar el CSV de pronósticos
    forecast_csv = "Combined_Sales_Data_forecast.csv"
    if os.path.exists(forecast_csv):
        df_forecast = pd.read_csv(forecast_csv)

        required_columns = ['ds', 'yhat', 'Animal']
        if all(col in df_forecast.columns for col in required_columns):
            # Convertir ds a datetime y extraer mes en español
            df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])
            df_forecast['month_en'] = df_forecast['ds'].dt.strftime('%B')

            english_to_spanish_months = {
                'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
                'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
                'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
            }

            df_forecast['month'] = df_forecast['month_en'].map(english_to_spanish_months)
            df_forecast['units_sold'] = df_forecast['yhat'].round().astype(int)

            # Unir con df_comida
            df_merged = pd.merge(df_forecast, df_comida, left_on='Animal', right_on='Animal', how='inner')

            # Materiales a considerar
            materiales = ['Trigo_g', 'Suplemento_Vitaminico_g', 'Heno_g', 'Agua_g']

            # Calcular las cantidades necesarias
            materiales_result = []
            for _, row in df_merged.iterrows():
                mes = row['month']
                animal = row['Animal']
                units = row['units_sold']

                for mat in materiales:
                    mat_name = mat.replace('_g', '').replace('_', ' ')
                    cantidad = int(units * row[mat])  # redondear a entero
                    materiales_result.append({
                        'month': mes,
                        'material_name': mat_name,
                        'animal_food': animal,
                        'quantity_needed': cantidad
                    })

            # Limpiar la tabla MaterialNeeded y MaterialSummary si se desea refrescar los datos
            MaterialNeeded.query.delete()
            MaterialSummary.query.delete()
            db.session.commit()

            # Insertar datos en MaterialNeeded
            material_records = [MaterialNeeded(**item) for item in materiales_result]
            db.session.bulk_save_objects(material_records)
            db.session.commit()

            print("Datos detallados de materiales cargados en la base de datos.")

            # Crear la tabla resumida
            # Agrupar por mes, animal_food, material_name y sumar quantity_needed
            df_materials = pd.DataFrame(materiales_result)
            df_summary = df_materials.groupby(['month', 'animal_food', 'material_name'], as_index=False)['quantity_needed'].sum()
            df_summary.rename(columns={'quantity_needed': 'total_quantity'}, inplace=True)

            # Insertar en MaterialSummary
            summary_records = [MaterialSummary(**row) for row in df_summary.to_dict(orient='records')]
            db.session.bulk_save_objects(summary_records)
            db.session.commit()

            print("Tabla resumida de materiales cargada en la base de datos.")

        else:
            print("Faltan columnas requeridas en el CSV de pronóstico.")
    else:
        print(f"No se encontró el archivo de pronóstico '{forecast_csv}'.")

# ------------------------------------------------------------------------------------
# RUTAS
# ------------------------------------------------------------------------------------

@app.route('/')
def index():
    animals = SalesData.query.with_entities(SalesData.animal).distinct().all()
    return render_template("index.html", animals=[animal[0] for animal in animals])

@app.route('/forecasting', methods=['GET'])
def forecasting():
    limit = request.args.get('limit', default=10, type=int)
    selected_animal = request.args.get('animal', default=None)

    forecast_csv = "Combined_Sales_Data_forecast.csv"
    if not os.path.exists(forecast_csv):
        print(f"Archivo de pronóstico '{forecast_csv}' no encontrado.")
        return render_template("forecasting.html", data=[], animals=["All"])

    df_forecast = pd.read_csv(forecast_csv)
    df_forecast.rename(columns={'ds': 'Mes', 'Animal': 'Animal', 'yhat': 'Forecast_Ventas'}, inplace=True)

    required_columns = ['Mes', 'Forecast_Ventas']
    if not all(col in df_forecast.columns for col in required_columns):
        print("Faltan columnas requeridas en el CSV de pronóstico.")
        return render_template("forecasting.html", data=[], animals=["All"])

    if selected_animal and selected_animal != "All":
        df_forecast = df_forecast[df_forecast['Animal'] == selected_animal]

    df_forecast['units_sold'] = df_forecast['Forecast_Ventas'].round().astype(int)
    price_mapping = {
        "Horses": 70000,
        "Cows": 50000,
        "Pig": 30000,
        "Chickens": 20000
    }
    df_forecast['revenue'] = df_forecast.apply(lambda row: row['units_sold'] * price_mapping.get(row['Animal'], 0), axis=1)

    df_forecast_limited = df_forecast.head(limit)
    data = df_forecast_limited[['Mes', 'Animal', 'units_sold', 'revenue']].to_dict(orient='records')
    animals = ["All"] + df_forecast['Animal'].unique().tolist()

    return render_template("forecasting.html", data=data, animals=animals)

@app.route('/forecast_data/<animal>', methods=['GET'])
def forecast_data(animal):
    limit = request.args.get('limit', default=100, type=int)
    forecast_csv = "Combined_Sales_Data_forecast.csv"

    if not os.path.exists(forecast_csv):
        return jsonify([])

    df_forecast = pd.read_csv(forecast_csv)
    required_columns = ['ds', 'yhat', 'Animal']
    if not all(col in df_forecast.columns for col in required_columns):
        return jsonify([])

    df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])

    # Filter data from 2024-01-01 onwards
    start_date = datetime(2024, 1, 1) 
    df_forecast = df_forecast[df_forecast['ds'] >= start_date]

    if animal == "All":
        sales_data = df_forecast.head(limit)
    else:
        sales_data = df_forecast[df_forecast['Animal'] == animal].head(limit)

    sales_data['date'] = sales_data['ds'].dt.strftime('%Y-%m-%d')
    sales_data = sales_data.rename(columns={'Animal': 'animal_food', 'yhat': 'units_sold'})
    price_mapping = {
        "Horses": 70000,
        "Cow": 50000,
        "Pig": 30000,
        "Chicken": 20000
    }
    sales_data['units_sold'] = sales_data['units_sold'].round().astype(int)
    sales_data['revenue'] = sales_data.apply(lambda row: row['units_sold'] * price_mapping.get(row['animal_food'], 0), axis=1)

    data = sales_data[['date', 'animal_food', 'units_sold', 'revenue']].to_dict(orient='records')
    return jsonify(data)

@app.route('/data/<animal>', methods=['GET'])
def data_route(animal):
    limit = request.args.get('limit', default=100, type=int)

    if animal == "All":
        sales_data = SalesData.query.limit(limit).all()
    else:
        sales_data = SalesData.query.filter_by(animal=animal).limit(limit).all()

    data = [{
        'date': sale.date.strftime('%Y-%m-%d'),
        'units_sold': sale.units_sold,
        'revenue': sale.revenue
    } for sale in sales_data]

    return jsonify(data)

@app.route('/materials', methods=['GET'])
def materials():
    return render_template("materials.html")

@app.route('/materials_data', methods=['GET'])
def materials_data():
    materials = MaterialNeeded.query.all()
    data = [material.to_dict() for material in materials]
    return jsonify(data)

@app.route('/materials_summary_data', methods=['GET'])
def materials_summary_data():
    """
    Endpoint para obtener los datos resumidos con posibilidad de limitar la cantidad.
    Parámetro ?limit=x
    Opciones: 0, 10, 100, 1000, 10000
    Si limit=0, retorna todos los datos.
    """
    limit = request.args.get('limit', default=0, type=int)
    start_date_str = request.args.get('start_date', default='2024-01-01') 

    try:
        start_date = datetime.fromisoformat(start_date_str)
    except ValueError:
        return jsonify({'error': 'Invalid start_date format. Use ISO 8601 format (e.g., 2024-01-01)'}), 400 

    query = MaterialSummary.query

    # Filter data from 2024-01-01 onwards
    query = query.filter(MaterialSummary.month >= start_date.strftime('%M')) 

    if limit > 0:
        summaries = query.limit(limit).all()
    else:
        summaries = query.all()

    data = [s.to_dict() for s in summaries]
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)