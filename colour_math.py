import numpy as np
from colour import XYZ_to_Lab, delta_E, XYZ_to_xy, SDS_ILLUMINANTS, SpectralShape
from colour.plotting import plot_chromaticity_diagram_CIE1931
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import colour 

def compute_response(reflectance,  illuminant, sensitivities, wb=False):
    response = reflectance.values.T @ np.diag(illuminant.values) @ sensitivities.values
    max_response = compute_response_perfect_reflector(sensitivities, illuminant)
    if wb:
        response /= max_response
    else:
        response /= max_response[1]
    return response


def compute_response_perfect_reflector(sensitivities, illuminant):
    response_test = np.diag(illuminant.values) @ sensitivities.values
    response_sum = np.sum(response_test, axis=0)
    
    return response_sum
def wb(response_macbeth, responses):
    
    r_Gain = response_macbeth[18, 0] / response_macbeth[18, 1]
    b_Gain = response_macbeth[18, 2] / response_macbeth[18, 1]
    
    gains = [r_Gain, 1, b_Gain]
    
    response_sensor = responses / gains
    return response_sensor

def deltae_stats_nm(coef, X, y, degree, RP, n_terms):

    M = coef.reshape((3, n_terms))
    result = colour.apply_matrix_colour_correction(
            X,
            M,
            method="Finlayson 2015",
            degree=degree,
            root_polynomial_expansion=RP,
    )
    
    deltae = delta_E(XYZ_to_Lab(result), y)
    
    error = np.mean(deltae)
    return error

def deltae_stats(a,b):
    sensor_lab = XYZ_to_Lab(a)
    human_lab = XYZ_to_Lab(b)
    
    deltae = delta_E(sensor_lab, human_lab)
    return deltae 

def deltae_mean(a,b):
    sensor_lab = XYZ_to_Lab(b)
    human_lab = XYZ_to_Lab(a)

    deltae = delta_E(sensor_lab, human_lab)
    return np.mean(deltae)

def deltae_stats_cross(estimator,a,b):
    sensor_response_estimator = estimator.predict(a)
    sensor_response_estimator = sensor_response_estimator / np.max(sensor_response_estimator)
    sensor_lab = XYZ_to_Lab(sensor_response_estimator)
    human_lab = XYZ_to_Lab(b)
    
    deltae = delta_E(human_lab, sensor_lab)
    return np.max(deltae)

def plot_chromaticity_diagram(responses_xyz):
    responses_xy = XYZ_to_xy(responses_xyz)
    plot_chromaticity_diagram_CIE1931(standalone=False)    

    plt.plot(responses_xy[:, 0], responses_xy[:, 1], 'bo', markersize=8)
    
    plt.plot([0.64,0.3, 0.15, 0.64],
        [0.33,0.60, 0.06, 0.33],
        color='white', linewidth=2)
    
    plt.show(block=True)
