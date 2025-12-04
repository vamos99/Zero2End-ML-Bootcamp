import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    İki nokta arasındaki Haversine mesafesini (km) hesaplar.
    Vektörize işlem (NumPy) kullanır, bu yüzden pandas Series veya numpy array ile çalışabilir.
    """
    R = 6371  # Dünya yarıçapı (km)

    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    d = R * c
    return d
