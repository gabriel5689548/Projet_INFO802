# services/ors_client.py

import openrouteservice as ors
from openrouteservice import convert
from config import ORS_API_KEY

def ors_directions(coord_start, coord_end):
    client = ors.Client(key=ORS_API_KEY)
    start_lonlat = (coord_start[1], coord_start[0])
    end_lonlat   = (coord_end[1], coord_end[0])
    return client.directions([start_lonlat, end_lonlat],
                             profile='driving-car',
                             instructions=True,
                             language='fr')
