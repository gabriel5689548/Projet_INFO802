# services/geocode.py
import requests

def geocode_place(place):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "MyFlaskApp/1.0"
    }
    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        return (lat, lon)
    except:
        return None
