import urllib.request
import json
import os

def download():
    url = "https://overpass-api.de/api/interpreter"
    # Construct overpass relation query for route=bus in Bhubaneswar bbox
    query = """[out:json][timeout:90];
relation["route"="bus"](20.211,85.732,20.367,85.904);
out geom;"""

    req = urllib.request.Request(url, data=query.encode('utf-8'), headers={'User-Agent': 'Antigravity-Agent/1.0'})
    print("Sending request to Overpass API...")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            data = json.loads(res_data)
            elements = data.get('elements', [])
            print(f"Successfully downloaded {len(elements)} elements.")
            
            # Save raw data
            dest_dir = os.path.join("data", "raw", "infrastructure")
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, "bhubaneswar_bus_routes.json")
            with open(dest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Saved raw data to {dest_file}")
    except Exception as e:
        print(f"Failed to query Overpass API: {e}")

if __name__ == "__main__":
    download()
