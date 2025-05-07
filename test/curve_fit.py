import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

# Logistic function
def logistic(x, A, k, V0, C):
    return A / (1 + np.exp(-k * (x - V0))) + C

# Function to fit the data and return the fitted parameters
def fit_light_intensity(data_file):
    """
    Fit the logistic function to the light intensity data.
    :param data_file: Path to the CSV file containing the calibration data.
    :return: Fitted parameters (A, k, V0, C)
    """
    # Load the data
    df = pd.read_csv(data_file)
    voltage = df["Voltage"].values
    intensity = df["uE"].values

    # Fit the logistic function
    popt, _ = curve_fit(logistic, voltage, intensity, p0=[4000, 2, 2.5, 0])
    return popt  # Return the fitted parameters

# Function to predict light intensity for a given voltage
def predict_light_intensity(voltage, params):
    """
    Predict the light intensity for a given voltage using the fitted parameters.
    :param voltage: Voltage input (float or numpy array).
    :param params: Fitted parameters (A, k, V0, C).
    :return: Predicted light intensity.
    """
    A, k, V0, C = params
    return logistic(voltage, A, k, V0, C)

# Example usage
if __name__ == "__main__":
    # Fit the data and get the parameters
    data_file = "./calibration/licor_red_led_calibration_random.csv"
    fitted_params = fit_light_intensity(data_file)

    # Predict light intensity for a specific voltage
    test_voltage = 1.74 # Example voltage
    predicted_intensity = predict_light_intensity(test_voltage, fitted_params)
    print(f"Predicted light intensity at {test_voltage} V: {predicted_intensity:.2f} uE")