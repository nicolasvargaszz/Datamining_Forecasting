# knn_model.py
import joblib
import numpy as np

# Load the KNN model (replace with your trained model's path)
knn_model = joblib.load("knn_model.pkl")

def predict_segment(age, gender, city, purchase_frequency, average_purchase_value, loyalty_score):
    # Prepare the data for prediction
    input_data = np.array([[age, gender, city, purchase_frequency, average_purchase_value, loyalty_score]])
    
    # Predict the customer segment
    predicted_segment = knn_model.predict(input_data)
    return predicted_segment[0]
