import zeep

def main():
    wsdl_url = "http://127.0.0.1:8000/?wsdl"
    client = zeep.Client(wsdl=wsdl_url)

    result = client.service.calculate_trip(
        436,  # distance_km
        90,   # avg_speed_kmh
        100,  # autonomy_km
        30,   # charge_time_min
        0.25  # cost_per_km
    )
    print("Réponse du service SOAP :", result)

if __name__ == "__main__":
    main()
