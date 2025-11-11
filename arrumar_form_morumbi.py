import requests

def get_lat_lon(address: str, country_codes: str = "br") -> tuple[float, float] | None:
    """
    Consulta a API Nominatim para geocodificar o endereço passado.
    Retorna (latitude, longitude) ou None se não encontrar.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "addressdetails": 1,
        "limit": 1,
        "countrycodes": country_codes,   # filtra para Brasil
        "accept-language": "pt-BR"
    }
    headers = {
        "User-Agent": "MinhaAplicacaoGeocoding/1.0 (email@dominio.com)"  # use um user‑agent identificável
    }
    response = requests.get(url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    first = data[0]
    lat = float(first["lat"])
    lon = float(first["lon"])
    return (lat, lon)

if __name__ == "__main__":
    endereco = "R. Mal. Hastimphilo de Moura, 27"
    resultado = get_lat_lon(endereco)
    if resultado:
        print(f"Latitude: {resultado[0]}, Longitude: {resultado[1]}")
    else:
        print("Endereço não encontrado.")
