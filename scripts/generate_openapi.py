import json
import os
import sys

# Add the project root to sys.path to allow importing from api
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from api.main import app

def generate_openapi_json():
    openapi_schema = app.openapi()
    output_path = os.path.join(project_root, "openapi.json")
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"OpenAPI schema generated at: {output_path}")

if __name__ == "__main__":
    generate_openapi_json()
