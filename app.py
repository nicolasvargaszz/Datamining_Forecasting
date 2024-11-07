from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales_data.db'
db = SQLAlchemy(app)

# Define the SalesData model
class SalesData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    animal = db.Column(db.String(50), nullable=False)
    units_sold = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    revenue = db.Column(db.Integer, nullable=False)

# Initialize the database
with app.app_context():
    db.create_all()

# Load the combined data CSV
df_combined = pd.read_csv("Supermix_Sales_data.csv")

# Rename columns for easier access
df_combined.rename(columns={
    'Date': 'date',
    'Animal': 'animal',
    'Price (Miles de Guaranies)': 'price',
    'Units Sold': 'units_sold'
}, inplace=True)

# Insert data into the database
with app.app_context():
    for _, row in df_combined.iterrows():
        record = SalesData(
            date=datetime.strptime(row['date'], '%Y-%m-%d'),
            animal=row['animal'],
            units_sold=row['units_sold'],
            price=row['price'],
            revenue=row['units_sold'] * row['price']
        )
        db.session.add(record)
    db.session.commit()

@app.route('/')
def index():
    # Get unique animals from the database
    animals = SalesData.query.with_entities(SalesData.animal).distinct().all()
    return render_template("index.html", animals=[animal[0] for animal in animals])

@app.route('/forecasting', methods=['GET'])
def forecasting():
    limit = request.args.get('limit', default=10, type=int)
    selected_animal = request.args.get('animal', default=None)

    # Load the combined forecasting data
    df_forecast = pd.read_csv("Combined_Sales_Data_forecast.csv")
    
    # Filter data for dates starting from 01/01/2024
    df_forecast['ds'] = pd.to_datetime(df_forecast['ds'])  # Convert to datetime
    df_forecast = df_forecast[df_forecast['ds'] >= '2024-01-01']

    # If an animal filter is provided (and not empty), filter the data by the selected animal
    if selected_animal and selected_animal != "All":
        df_forecast = df_forecast[df_forecast['Animal'] == selected_animal]

    # Price mapping for different animals
    price_mapping = {
        "Cow": 50000,
        "Pigs": 30000,
        "Chicken": 20000,
        "Horses": 70000,
        # Add more as needed
    }

    # Calculate revenue and round units sold
    df_forecast['units_sold'] = df_forecast['yhat'].round().astype(int)
    df_forecast['revenue'] = df_forecast.apply(lambda row: price_mapping.get(row['Animal'], 0) * row['units_sold'], axis=1)

    # Serialize the data
    data = df_forecast[['ds', 'Animal', 'units_sold', 'revenue']].head(limit).to_dict(orient='records')
    
    # Format the date and keep the Animal key
    for item in data:
        item['date'] = item.pop('ds').strftime('%Y-%m-%d')  # Format the date
    
    # Pass the list of unique animals for the filter dropdown
    animals = ["All"] + df_forecast['Animal'].unique().tolist()

    return render_template("forecasting.html", data=data, animals=animals)

@app.route('/data/<animal>', methods=['GET'])
def data(animal):
    # Get the limit from query parameters, default to 100
    limit = request.args.get('limit', default=100, type=int)
    
    # Fetch data with the limit
    sales_data = SalesData.query.filter_by(animal=animal).limit(limit).all()
    
    # Serialize the data
    data = [
        {
            'date': sale.date.strftime('%Y-%m-%d'), 
            'units_sold': sale.units_sold, 
            'revenue': sale.revenue
        } 
        for sale in sales_data
    ]
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
