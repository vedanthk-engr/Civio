import os
import httpx


GOOGLE_MAPS_API_KEY = os.environ.get("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY")

async def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Perform reverse geocoding to retrieve address and ward details.
    """
    if GOOGLE_MAPS_API_KEY:
        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={GOOGLE_MAPS_API_KEY}"
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                res = r.json()
                if res.get("status") == "OK" and res.get("results"):
                    best_match = res["results"][0]
                    address = best_match.get("formatted_address")
                    # Try to parse ward/zone from components
                    ward = "Indiranagar"
                    zone = "East Zone"
                    for comp in best_match.get("address_components", []):
                        types = comp.get("types", [])
                        if "sublocality" in types or "neighborhood" in types:
                            name = comp.get("long_name")
                            if name in ["Koramangala", "HSR Layout", "Whitefield", "Jayanagar", "Malleshwaram"]:
                                ward = name
                    
                    if ward == "Koramangala": zone = "South Zone"
                    elif ward == "Whitefield": zone = "Mahadevapura Zone"
                    elif ward == "Jayanagar": zone = "South Zone"
                    elif ward == "Malleshwaram": zone = "West Zone"
                    elif ward == "HSR Layout": zone = "Bommanahalli Zone"
                    
                    return {
                        "address": address,
                        "ward": ward,
                        "zone": zone
                    }
        except Exception as e:
            print(f"Google Maps geocoding failed: {e}")
            
    # Mock fallback based on coordinates bounding box
    ward = "Indiranagar"
    zone = "East Zone"
    road = "100 Feet Road"
    
    # Simple bounding boxes matching vertex_service
    if 12.92 <= lat <= 12.948 and 77.61 <= lng <= 77.64:
        ward = "Koramangala"
        zone = "South Zone"
        road = "80 Feet Road, Koramangala 4th Block"
    elif 12.95 <= lat <= 12.99 and 77.73 <= lng <= 77.77:
        ward = "Whitefield"
        zone = "Mahadevapura Zone"
        road = "ITPB Main Road, Whitefield"
    elif 12.915 <= lat <= 12.942 and 77.57 <= lng <= 77.595:
        ward = "Jayanagar"
        zone = "South Zone"
        road = "9th Main Road, Jayanagar 3rd Block"
    elif 12.985 <= lat <= 13.01 and 77.555 <= lng <= 77.58:
        ward = "Malleshwaram"
        zone = "West Zone"
        road = "Margosa Road, Malleshwaram"
    elif 12.895 <= lat <= 12.925 and 77.63 <= lng <= 77.66:
        ward = "HSR Layout"
        zone = "Bommanahalli Zone"
        road = "27th Main Road, HSR Sector 2"
        
    return {
        "address": f"No. 42, {road}, Bengaluru, Karnataka, 560001",
        "ward": ward,
        "zone": zone
    }
