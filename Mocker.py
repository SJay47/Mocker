from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from faker import Faker

# Initialize Faker
fake = Faker()

# API Configuration (update with your actual values)
API_CONFIG = {
    "API_BASE_URL": "http://localhost",
    "KEYCLOAK_TOKEN_URL": "http://localhost:18080/realms/primecare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID": "primecare-frontend-postman",
    "ADMIN_USERNAME": "alice@demo.com",
    "ADMIN_PASSWORD": "q",
    "ORGANIZATION_ID": "b563a085-e9b1-4bec-8570-f20dca7ccda4",
    "DATASET_ID": "ce83ce9c-0349-436f-80bf-a165cea5f905",
}


def custom_generate(data: Any) -> Any:
    """
    Recursively processes JSON data to mock ONLY the numerical values within
    'statistics' blocks, based on the Croissant fingerprint format.

    - All textual fields ('name', 'description', etc.) are preserved.
    - Differentiates between numerical and categorical statistics.
    - In 'category_frequencies', it preserves the category names (keys) and
      only mocks their numerical counts (values).
    """
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            # Main logic for mocking only the 'statistics' block
            if key.lower() == "statistics" and isinstance(value, dict):
                stats_data = value.copy()  # Work on a copy of the original statistics
                new_stats = stats_data.copy()

                # --- Numerical Field Mocking ---
                # Check for 'min' key to identify numerical stats blocks.
                if "min" in stats_data:
                    is_float = isinstance(stats_data.get("min"), float) or isinstance(
                        stats_data.get("mean"), float
                    )

                    if is_float:
                        min_val = fake.pyfloat(
                            min_value=10, max_value=40, right_digits=2
                        )
                        max_val = fake.pyfloat(
                            min_value=min_val + 50, max_value=150, right_digits=2
                        )
                    else:
                        min_val = fake.random_int(min=10, max=40)
                        max_val = fake.random_int(min=min_val + 50, max=100)

                    # Generate consistent percentiles/quartiles
                    p5 = fake.pyfloat(
                        min_value=min_val,
                        max_value=min_val + (max_val - min_val) * 0.1,
                        right_digits=2,
                    )
                    q1 = fake.pyfloat(
                        min_value=p5,
                        max_value=min_val + (max_val - min_val) * 0.3,
                        right_digits=2,
                    )
                    median = fake.pyfloat(
                        min_value=q1,
                        max_value=min_val + (max_val - min_val) * 0.6,
                        right_digits=2,
                    )
                    q3 = fake.pyfloat(
                        min_value=median, max_value=max_val * 0.9, right_digits=2
                    )
                    p95 = fake.pyfloat(min_value=q3, max_value=max_val, right_digits=2)
                    mean_val = fake.pyfloat(min_value=q1, max_value=q3, right_digits=2)

                    # Overwrite numerical values in the new_stats dictionary
                    for stat_key in new_stats:
                        if stat_key == "min":
                            new_stats[stat_key] = (
                                round(min_val) if not is_float else min_val
                            )
                        elif stat_key == "max":
                            new_stats[stat_key] = (
                                round(max_val) if not is_float else max_val
                            )
                        elif stat_key == "mean":
                            new_stats[stat_key] = (
                                round(mean_val) if not is_float else mean_val
                            )
                        elif stat_key == "median":
                            new_stats[stat_key] = (
                                round(median) if not is_float else median
                            )
                        elif stat_key == "stdDev":
                            new_stats[stat_key] = fake.pyfloat(
                                min_value=5, max_value=20, right_digits=2
                            )
                        elif stat_key == "unique_count":
                            new_stats[stat_key] = fake.random_int(min=20, max=100)
                        elif stat_key == "missing_count":
                            new_stats[stat_key] = fake.random_int(min=0, max=50)
                        elif stat_key == "quartile_1":
                            new_stats[stat_key] = round(q1) if not is_float else q1
                        elif stat_key == "quartile_3":
                            new_stats[stat_key] = round(q3) if not is_float else q3
                        elif stat_key == "percentile_5":
                            new_stats[stat_key] = round(p5) if not is_float else p5
                        elif stat_key == "percentile_95":
                            new_stats[stat_key] = round(p95) if not is_float else p95
                        elif stat_key == "skewness":
                            new_stats[stat_key] = fake.pyfloat(
                                min_value=-1, max_value=1, right_digits=2
                            )
                        elif stat_key == "kurtosis":
                            new_stats[stat_key] = fake.pyfloat(
                                min_value=-1, max_value=1, right_digits=2
                            )
                        elif stat_key == "histogram" and isinstance(
                            stats_data[stat_key], dict
                        ):
                            original_hist = stats_data[stat_key]
                            if "counts" in original_hist:
                                num_counts = len(original_hist["counts"])
                                new_stats[stat_key]["counts"] = [
                                    fake.random_int(min=100, max=2000)
                                    for _ in range(num_counts)
                                ]

                # --- Categorical Field Mocking ---
                # Check for 'mode' key to identify categorical stats blocks.
                elif "mode" in stats_data:
                    for stat_key in new_stats:
                        # Mock only the numerical values
                        if stat_key in [
                            "unique_count",
                            "missing_count",
                            "mode_frequency",
                        ]:
                            new_stats[stat_key] = fake.random_int(min=0, max=5000)
                        elif stat_key == "entropy":
                            new_stats[stat_key] = fake.pyfloat(
                                min_value=0.5, max_value=3.0, right_digits=2
                            )
                        # For category_frequencies, keep keys and mock values
                        elif stat_key == "category_frequencies" and isinstance(
                            stats_data[stat_key], dict
                        ):
                            original_cats = stats_data[stat_key]
                            mocked_cats = {}
                            for category_name in original_cats:
                                mocked_cats[category_name] = fake.random_int(
                                    min=100, max=3000
                                )
                            new_stats[stat_key] = mocked_cats

                new_data[key] = new_stats
            else:
                # For all other fields, preserve them but process nested structures
                new_data[key] = custom_generate(value)
        return new_data

    if isinstance(data, list):
        return [custom_generate(item) for item in data]

    # Return all primitive values (strings, numbers, etc.) and non-dict/list items unchanged
    return data


def save_mocked_fingerprint(fp: dict, filename: str, output_dir: Path):
    """
    Save the fingerprint JSON to a file inside the specified folder.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / filename
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(fp, f, indent=2)
    return file_path


def read_json_template(file_path: Path) -> dict:
    """
    Read a JSON file and return its contents as a dictionary.
    """
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
        return {}
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return {}


def get_access_token() -> Optional[str]:
    """
    Authenticate with Keycloak and get an access token.
    """
    token_url = API_CONFIG["KEYCLOAK_TOKEN_URL"]
    payload = {
        "client_id": API_CONFIG["KEYCLOAK_CLIENT_ID"],
        "grant_type": "password",
        "username": API_CONFIG["ADMIN_USERNAME"],
        "password": API_CONFIG["ADMIN_PASSWORD"],
    }
    try:
        response = requests.post(token_url, data=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as e:
        print(f"Authentication error: {e}")
        return None


def post_fingerprint(fingerprint: Dict[str, Any], access_token: str) -> bool:
    """
    POST the fingerprint to the API.
    """
    org_id = API_CONFIG["ORGANIZATION_ID"]
    dataset_id = API_CONFIG["DATASET_ID"]
    api_url = f"{API_CONFIG['API_BASE_URL']}/api/organizations/{org_id}/datasets/{dataset_id}/fingerprints"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_url, json=fingerprint, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"Successfully posted fingerprint. Response: {response.status_code}")
        return True
    except requests.RequestException as e:
        print(f"Error posting fingerprint: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return False


def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate and send mock Croissant fingerprints."
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=10,
        help="Number of mocks to generate per template.",
    )
    parser.add_argument(
        "--send",
        "-s",
        action="store_true",
        help="Send generated fingerprints to the API.",
    )
    parser.add_argument(
        "--templates-dir",
        "-t",
        type=str,
        default="templates",
        help="Directory for template JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="mock_fingerprints",
        help="Directory to save generated mocks.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    templates_dir = Path(args.templates_dir)
    output_dir = Path(args.output_dir)

    if not templates_dir.exists() or not any(templates_dir.iterdir()):
        print(
            f"Templates directory '{templates_dir}' is missing or empty. Creating it."
        )
        templates_dir.mkdir(exist_ok=True)
        print(
            f"Please add your 'Example fingerprint.json' to the '{templates_dir}' directory and rerun."
        )
        return

    json_files = list(templates_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in '{templates_dir}'.")
        return

    print(
        f"Found {len(json_files)} JSON template(s). Generating {args.count} mock(s) from each."
    )

    access_token = get_access_token() if args.send else None
    if args.send and not access_token:
        print("Failed to get access token. Will only generate local files.")

    all_fingerprints = []
    for json_file in json_files:
        print(f"\nProcessing template: {json_file.name}")
        template_data = read_json_template(json_file)
        if not template_data:
            print(f"Skipping invalid template: {json_file.name}")
            continue

        for i in range(args.count):
            print(f"  Generating mock {i + 1}/{args.count}...")
            mocked_data = custom_generate(template_data)

            # Add datasetId from config
            if "data" in mocked_data and isinstance(mocked_data["data"], dict):
                mocked_data["data"]["datasetId"] = API_CONFIG["DATASET_ID"]

            output_filename = f"mock_{json_file.stem}_{i + 1}.json"
            save_mocked_fingerprint(mocked_data, output_filename, output_dir)
            print(f"  Saved to '{output_dir / output_filename}'.")
            all_fingerprints.append(mocked_data)

    if access_token and args.send:
        print(f"\nSending {len(all_fingerprints)} mock fingerprints to the API...")
        success_count = sum(
            1 for fp in all_fingerprints if post_fingerprint(fp, access_token)
        )
        print(
            f"\nSuccessfully sent {success_count} of {len(all_fingerprints)} fingerprints."
        )

    print("\nScript finished.")


if __name__ == "__main__":
    main()
