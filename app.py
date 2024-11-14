# app.py

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import pandas as pd
import os
from flask_cors import CORS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define the SalesData model
class SalesData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    animal = db.Column(db.String(50), nullable=False)
    units_sold = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Integer, nullable=False)

# Define the MaterialNeeded model
class MaterialNeeded(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False)
    material_name = db.Column(db.String(50), nullable=False)
    animal_food = db.Column(db.String(50), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False)  # liters or kg

    def to_dict(self):
        return {
            'month': self.month,
            'material_name': self.material_name,
            'animal_food': self.animal_food,
            'quantity_needed': self.quantity_needed
        }

# Function to load sales data from CSV
def load_sales_data(csv_path):
    if not os.path.exists(csv_path):
        print(f"Sales data CSV file '{csv_path}' not found.")
        return []
    df = pd.read_csv(csv_path)
    # Ensure required columns are present
    required_columns = ['Date', 'Animal', 'Price (Miles de Guaranies)', 'Units Sold']
    if not all(col in df.columns for col in required_columns):
        print(f"Sales CSV missing required columns. Found columns: {df.columns.tolist()}")
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
            record = SalesData(
                date=datetime.strptime(row['date'], '%Y-%m-%d'),
                animal=row['animal'],
                units_sold=row['units_sold'],
                price=row['price'],
                revenue=row['units_sold'] * row['price']
            )
            records.append(record)
        except Exception as e:
            print(f"Error processing row {row}: {e}")
    return records

# Function to calculate materials needed based on forecast data
def calculate_materials_necesarias(df_forecast, df_comida):
    # Convert 'ds' to datetime and extract month in English
    df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])
    df_forecast['month_en'] = df_forecast['ds'].dt.strftime('%B')  # Full month name in English
    
    # Mapping from English to Spanish month names
    english_to_spanish_months = {
        'January': 'Enero',
        'February': 'Febrero',
        'March': 'Marzo',
        'April': 'Abril',
        'May': 'Mayo',
        'June': 'Junio',
        'July': 'Julio',
        'August': 'Agosto',
        'September': 'Septiembre',
        'October': 'Octubre',
        'November': 'Noviembre',
        'December': 'Diciembre'
    }
    
    # Apply the mapping
    df_forecast['month'] = df_forecast['month_en'].map(english_to_spanish_months)
    
    # Group by month and animal, sum 'yhat' to get total bags sold per animal per month
    grouped = df_forecast.groupby(['month', 'Animal'])['yhat'].sum().reset_index()
    
    resultados = []
    
    for _, row in grouped.iterrows():
        mes = row['month']
        animal = row['Animal']
        bags_sold = row['yhat']
    
        # Get proportions from df_comida
        comida_row = df_comida[df_comida['Animal'] == animal]
        if comida_row.empty:
            print(f"No se encontraron proporciones de comida para {animal}.")
            continue
        comida = comida_row.iloc[0]
    
        # Calculate materials needed based on animal
        if animal == 'Horses':
            litros_heno = bags_sold * comida['Heno_Litros']
            resultados.append({
                'month': mes,
                'material_name': 'Heno',
                'animal_food': animal,
                'quantity_needed': litros_heno
            })
        elif animal == 'Cows':
            litros_granos = bags_sold * comida['Granos_Litros']
            resultados.append({
                'month': mes,
                'material_name': 'Granos',
                'animal_food': animal,
                'quantity_needed': litros_granos
            })
        elif animal == 'Pigs':
            kg_suplemento = bags_sold * comida['Suplemento_Vitamínico_Kg']
            resultados.append({
                'month': mes,
                'material_name': 'Suplemento Vitamínico',
                'animal_food': animal,
                'quantity_needed': kg_suplemento
            })
        elif animal == 'Chickens':
            litros_agua = bags_sold * comida['Agua_Litros']
            resultados.append({
                'month': mes,
                'material_name': 'Agua',
                'animal_food': animal,
                'quantity_needed': litros_agua
            })
        else:
            print(f"Tipo de animal desconocido: {animal}")
    
    return resultados

# Initialize the database and load data if empty
with app.app_context():
    db.create_all()

    # Load sales data
    if SalesData.query.first() is None:
        sales_records = load_sales_data("Supermix_Sales_data.csv")
        if sales_records:
            db.session.bulk_save_objects(sales_records)
            db.session.commit()
            print("Sales data loaded into the database.")
        else:
            print("No sales data loaded.")

    # Load materials proportions
    data_comida = {
        'Animal': [
            'Horses',
            'Cows',
            'Pigs',
            'Chickens'
        ],
        'Heno_Litros': [4, 3, 2, 1],           # Proporciones de heno en litros
        'Granos_Litros': [2, 4, 3, 1],        # Proporciones de granos en litros
        'Suplemento_Vitamínico_Kg': [0.5, 0.6, 0.4, 0.2],  # Proporciones de suplemento vitamínico en kg
        'Agua_Litros': [1, 2, 1.5, 0.5]       # Proporciones de agua en litros
    }

    df_comida = pd.DataFrame(data_comida)

    # Check if materials data is already populated
    if MaterialNeeded.query.first() is None:
        # Check if forecast CSV exists
        forecast_csv = "Combined_Sales_Data_forecast.csv"
        if os.path.exists(forecast_csv):
            try:
                df_forecast = pd.read_csv(forecast_csv)
                # Ensure necessary columns are present
                required_columns = ['ds', 'yhat', 'Animal']
                if not all(col in df_forecast.columns for col in required_columns):
                    print(f"Forecast CSV missing required columns. Found columns: {df_forecast.columns.tolist()}")
                else:
                    # Calculate materials needed
                    materials = calculate_materials_necesarias(df_forecast, df_comida)

                    # Insert materials data into the database
                    material_records = [MaterialNeeded(**item) for item in materials]
                    db.session.bulk_save_objects(material_records)
                    db.session.commit()
                    print("Materials needed data loaded into the database.")
            except Exception as e:
                print(f"Error processing forecast data: {e}")
        else:
            print(f"Forecast CSV file '{forecast_csv}' not found.")

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
        print(f"Forecast CSV file '{forecast_csv}' not found.")
        data = []
        animals = ["All"]
    else:
        df_forecast = pd.read_csv(forecast_csv)
        df_forecast.rename(columns={
            'ds': 'Mes',
            'Animal': 'Animal',
            'yhat': 'Forecast_Ventas'
        }, inplace=True)

        # Ensure necessary columns are present
        required_columns = ['Mes', 'Forecast_Ventas']
        if not all(col in df_forecast.columns for col in required_columns):
            print(f"Forecast CSV missing required columns. Found columns: {df_forecast.columns.tolist()}")
            data = []
            animals = ["All"]
        else:
            # If 'Animal' column is present, we can filter based on it
            if selected_animal and selected_animal != "All":
                df_forecast = df_forecast[df_forecast['Animal'] == selected_animal]

            # Calculate units_sold and revenue per month
            # Assuming 'Forecast_Ventas' represents forecasted bags sold
            df_forecast['units_sold'] = df_forecast['Forecast_Ventas'].round().astype(int)
            # Define a price mapping if needed, else set revenue as 0 or remove
            price_mapping = {
                "Horses": 70000,
                "Cows": 50000,
                "Pigs": 30000,
                "Chickens": 20000
            }
            df_forecast['revenue'] = df_forecast.apply(lambda row: row['units_sold'] * price_mapping.get(row['Animal'], 0), axis=1)

            # Limit the data
            df_forecast_limited = df_forecast.head(limit)
            data = df_forecast_limited[['Mes', 'Animal', 'units_sold', 'revenue']].to_dict(orient='records')

            # Get distinct animals
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

    if animal == "All":
        sales_data = df_forecast.head(limit)
    else:
        sales_data = df_forecast[df_forecast['Animal'] == animal].head(limit)

    # Convert 'ds' to date and format
    sales_data['ds'] = pd.to_datetime(sales_data['ds'])
    sales_data['date'] = sales_data['ds'].dt.strftime('%d-%m-%Y')

    # Rename columns for consistency
    sales_data = sales_data.rename(columns={'Animal': 'animal_food', 'yhat': 'units_sold'})

    # Calculate revenue based on animal_food and units_sold
    price_mapping = {
        "Horses": 70000,
        "Cows": 50000,
        "Pigs": 30000,
        "Chickens": 20000
    }
    sales_data['revenue'] = sales_data.apply(lambda row: row['units_sold'] * price_mapping.get(row['animal_food'], 0), axis=1)

    data = sales_data[['date', 'animal_food', 'units_sold', 'revenue']].to_dict(orient='records')

    return jsonify(data)

@app.route('/data/<animal>', methods=['GET'])
def data(animal):
    limit = request.args.get('limit', default=100, type=int)
    
    if animal == "All":
        sales_data = SalesData.query.limit(limit).all()
    else:
        sales_data = SalesData.query.filter_by(animal=animal).limit(limit).all()
    
    data = [
        {
            'date': sale.date.strftime('%Y-%m-%d'), 
            'units_sold': sale.units_sold, 
            'revenue': sale.revenue
        } 
        for sale in sales_data
    ]
    
    return jsonify(data)

@app.route('/materials', methods=['GET'])
def materials():
    return render_template("materials.html")

@app.route('/materials_data', methods=['GET'])
def materials_data():
    # Fetch all materials needed for 2024
    materials = MaterialNeeded.query.all()
    data = [material.to_dict() for material in materials]
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
