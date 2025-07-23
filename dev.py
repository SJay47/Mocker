# File: Mocker.py
from __future__ import annotations

import argparse
import json
import random
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from faker import Faker

# --- UNCHANGED: Basic Setup & API Config ---
ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TPL = ROOT_DIR / "templates" / "master_fingerprint_template.json" 
DEFAULT_OUTDIR = ROOT_DIR / "mock_outputs"

API_CONFIG = {
    "API_BASE_URL": "https://dev-ppfl-api.asclepyus.com",
    "KEYCLOAK_TOKEN_URL": "https://dev-ppfl-auth.asclepyus.com/keycloak/admin/realms/PrimeCare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID": "public-dev-ppfl-api-swagger",
    "ADMIN_USERNAME": "alice@demo.com",
    "ADMIN_PASSWORD": "123",
    "ORGANIZATION_ID": "6770514c-b074-4b85-80c5-924b5ef77abb",
    "DATASET_ID": "ad229b50-1a4f-47f8-b15a-5e34a12681d2"
}

fake = Faker()
random.seed()
Faker.seed()

# --- NEW: Field Name Variation Dictionary ---
# This dictionary drives the variation in field names to test semantic mapping.
FIELD_NAME_VARIANTS = {
    # --- Variations for Patient Demographics ---
    "patient_demographics/patient_age": [
        "age", 
        "Age", 
        "patient_age",
        "Patient Age", 
        "patient_age_in_years",
        "age_years",
        "DEMO_AGE",
        "ageAtAdmission",
        "Age_in_Yr"
    ],
    "patient_demographics/patient_blood_type": [
        "blood_type", 
        "Blood Group", 
        "BloodType",
        "patient_blood_group",
        "bloodgroup",
        "BT",
        "LAB_BloodType"
    ],

    # --- Variations for Vital Signs ---
    "vital_signs/bmi": [
        "BMI", 
        "body_mass_index", 
        "Body Mass Index",
        "patient_bmi_value",
        "vitals_bmi",
        "V_BMI"
    ],

    # --- Variations for Clinical Notes ---
    "clinical_notes/notes": [
        "notes", 
        "clinical_notes", 
        "physician_notes",
        "Clinical Observations",
        "doctor_notes",
        "progress_notes",
        "TXT_NOTES"
    ],
    
    # --- NEW: Adding variations for other potential fields you might add ---
    "patient_demographics/gender": [
        "gender",
        "sex",
        "Patient Gender",
        "sex_of_patient",
        "DEMO_GNDR"
    ],
    "vital_signs/heart_rate": [
        "heart_rate",
        "HeartRate",
        "pulse",
        "vitals_hr",
        "HR"
    ],
    "vital_signs/blood_pressure_systolic": [
        "systolic_bp",
        "BloodPressure_Systolic",
        "SBP",
        "V_SYS"
    ],
    "vital_signs/blood_pressure_diastolic": [
        "diastolic_bp",
        "BloodPressure_Diastolic",
        "DBP",
        "V_DIA"
    ],
    "lab_results/cholesterol": [
        "cholesterol",
        "Total Cholesterol",
        "CHOL_Total",
        "lab_chol"
    ],
    "medical_condition/diagnosis": [
        "diagnosis",
        "primary_diagnosis",
        "Condition",
        "ICD10_Code",
        "DIAG_PRIMARY"
    ]
}



# --- NEW: Expanded and More Realistic Fingerprint Profiles ---
# Each profile now controls which record sets, extensions, and field descriptions to include.
FINGERPRINT_PROFILES = [
    {
        "name": "Rich_MultiModal",
        "record_set_ids": ["patient_demographics", "vital_signs", "clinical_notes", "medical_images"],
        "extensions_to_keep": ["ex:", "stat:", "jsd:"], # Keep all extensions
        "include_descriptions": True,
        "weight": 10
    },
    {
        "name": "Classic_Tabular_With_Stats",
        "record_set_ids": ["patient_demographics", "vital_signs"],
        "extensions_to_keep": ["stat:"], # Only keep statistics
        "include_descriptions": True,
        "weight": 20
    },
    {
        "name": "Imaging_Only_No_Extensions",
        "record_set_ids": ["medical_images"],
        "extensions_to_keep": [], # Strip all extensions
        "include_descriptions": True,
        "weight": 15
    },
    {
        "name": "Text_Heavy_With_JSD",
        "record_set_ids": ["patient_demographics", "clinical_notes"],
        "extensions_to_keep": ["jsd:"], # Only keep JSD
        "include_descriptions": True,
        "weight": 15
    },
    {
        "name": "Abbreviated_Clinical_No_Descriptions",
        "record_set_ids": ["patient_demographics", "vital_signs"],
        "extensions_to_keep": [], # No extensions
        "include_descriptions": False, # Test semantic matching on names alone
        "weight": 15
    },
    {
        "name": "Purely_Descriptive_No_Records",
        "record_set_ids": [], # No record sets, like some real examples
        "extensions_to_keep": [],
        "include_descriptions": True,
        "weight": 10
    },
    {
        "name": "Minimalist_Vital_Signs_Only",
        "record_set_ids": ["vital_signs"],
        "extensions_to_keep": [],
        "include_descriptions": False,
        "weight": 15
    },
]

# --- UNCHANGED HELPER FUNCTIONS: rand_float, _norm_dist ---
def rand_float(lo: float, hi: float, digits: int = 2) -> float:
    return round(random.uniform(lo, hi), digits)

def _norm_dist(v):
    s = sum(v) or 1
    return [round(x / s, 6) for x in v]

# --- UNCHANGED MOCKING FUNCTIONS: These generate the full data before it's tailored by a profile ---
def mock_dataset_stats() -> dict:
    pos = fake.random_int(100, 10000)
    neg = fake.random_int(100, 10000)
    total = pos + neg
    p_pos = pos / total if total > 0 else 0
    p_neg = neg / total if total > 0 else 0
    entropy = -(p_pos * math.log2(p_pos) + p_neg * math.log2(p_neg)) if p_pos > 0 and p_neg > 0 else 0
    return {
        "@type": "ex:DatasetStatistics",
        "ex:labelDistribution": {"@type": "ex:LabelDistribution", "ex:positive": pos, "ex:negative": neg},
        "ex:labelSkewAlpha": rand_float(0.1, 1.5, 4),
        "ex:labelEntropy": round(entropy, 4),
        "ex:featureStatsVector": [rand_float(0, 100) for _ in range(6)],
        "ex:modelSignature": f"sha256:{fake.sha256()}",
    }

def mock_numeric_stats(template: dict) -> dict:
    stats = {"@type": "stat:Statistics"}
    if "stat:min" in template: stats["stat:min"] = rand_float(10, 40)
    if "stat:max" in template: stats["stat:max"] = rand_float(80, 150)
    if "stat:mean" in template: stats["stat:mean"] = rand_float(40, 80)
    if "stat:median" in template: stats["stat:median"] = stats["stat:mean"] + rand_float(-5, 5)
    if "stat:stdDev" in template: stats["stat:stdDev"] = rand_float(5, 20)
    if "stat:unique_count" in template: stats["stat:unique_count"] = fake.random_int(50, 100)
    if "stat:missing_count" in template: stats["stat:missing_count"] = fake.random_int(0, 500)
    if "stat:skewness" in template: stats["stat:skewness"] = rand_float(-1, 1)
    if "stat:kurtosis" in template: stats["stat:kurtosis"] = rand_float(-1, 1)
    if "stat:histogram" in template:
        num_bins = len(template["stat:histogram"]["stat:bins"])
        new_bins = sorted([rand_float(10, 200) for _ in range(num_bins)])
        stats["stat:histogram"] = {
            "stat:bins": new_bins,
            "stat:counts": [fake.random_int(100, 3000) for _ in range(num_bins - 1)],
        }
    return stats

def mock_categorical_stats(template: dict) -> dict:
    stats = {"@type": "stat:Statistics"}
    category_template = template.get("stat:category_frequencies", {})
    original_categories = list(category_template.keys())
    if "stat:unique_count" in template: stats["stat:unique_count"] = len(original_categories)
    if "stat:missing_count" in template: stats["stat:missing_count"] = fake.random_int(0, 500)
    if "stat:mode" in template and original_categories: stats["stat:mode"] = random.choice(original_categories)
    if "stat:mode_frequency" in template: stats["stat:mode_frequency"] = fake.random_int(1000, 5000)
    if "stat:entropy" in template: stats["stat:entropy"] = rand_float(1, 4)
    if original_categories:
        stats["stat:category_frequencies"] = {category: fake.random_int(100, 3000) for category in original_categories}
    return stats

def mock_image_stats() -> dict:
    min_w, max_w = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    min_h, max_h = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    return {
        "@type": "ex:ImageStatistics", "ex:numImages": fake.random_int(500, 10000),
        "ex:imageDimensions": {"ex:minWidth": min_w, "ex:maxWidth": max_w, "ex:minHeight": min_h, "ex:maxHeight": max_h},
        "ex:colorMode": random.choice(["grayscale", "RGB"]), "ex:modality": random.choice(["X-ray", "MRI", "CT Scan"]),
    }

def mock_annotation_stats() -> dict:
    classes = sorted({*fake.words(nb=random.randint(2, 8), ext_word_list=["nodule", "fracture", "tumor"])})
    return {
        "@type": "ex:AnnotationStatistics", "ex:numAnnotations": fake.random_int(1000, 50000),
        "ex:numClasses": len(classes), "ex:classes": classes,
        "ex:objectsPerImage": {"ex:avg": rand_float(1, 5, 2), "ex:median": fake.random_int(1, 4)},
        "ex:boundingBoxStats": {"ex:avgRelativeWidth": rand_float(0.1, 0.5), "ex:avgRelativeHeight": rand_float(0.1, 0.5)},
    }

def mock_jsd_stats() -> dict:
    tokens = [fake.word() for _ in range(5)]
    probs = _norm_dist([random.random() for _ in tokens])
    return {
        "@type": "jsd:TextDistribution", "jsd:total_records_analyzed": fake.random_int(500, 10000),
        "jsd:language": "en", "jsd:vocabulary_size": len(tokens),
        "jsd:top_k_tokens": [{"jsd:token": t, "jsd:frequency": p} for t, p in zip(tokens, probs)],
        "jsd:token_probability_vector": probs,
    }

# --- REWRITTEN/NEW: Main logic for creating and tailoring fingerprints ---

def _strip_unwanted_keys(node: Any, allowed_prefixes: List[str]) -> Any:
    """Recursively removes keys from a dictionary that do not start with an allowed prefix."""
    if isinstance(node, dict):
        # Create a copy of keys to iterate over, as we'll be modifying the dict
        for key in list(node.keys()):
            # Check if the key is a custom extension (e.g., "ex:datasetStats")
            if ":" in key and not any(key.startswith(prefix) for prefix in allowed_prefixes):
                del node[key]
            else:
                # Recurse into the value
                node[key] = _strip_unwanted_keys(node[key], allowed_prefixes)
    elif isinstance(node, list):
        # Recurse into each item in the list
        return [_strip_unwanted_keys(item, allowed_prefixes) for item in node]
    return node

def create_fingerprint(template: Dict, profile: Dict) -> Dict:
    """Creates a single mocked fingerprint, tailored by a profile."""
    
    # 1. Generate the full-featured fingerprint from the master template
    fp_mocked = generate_mock_data(deepcopy(template))
    croissant_body = fp_mocked["data"]["rawFingerprintJson"]
    
    # 2. Apply Profile: Filter Record Sets
    all_record_sets = croissant_body["recordSet"]
    profiled_record_sets = [rs for rs in all_record_sets if rs["@id"] in profile["record_set_ids"]]
    croissant_body["recordSet"] = profiled_record_sets

    # 3. Apply Profile: Vary field names for semantic matching tests
    for rs in croissant_body["recordSet"]:
        for field in rs.get("field", []):
            original_id = field["@id"]
            if original_id in FIELD_NAME_VARIANTS:
                new_name = random.choice(FIELD_NAME_VARIANTS[original_id])
                # To keep it simple, we'll use the new name for both name and ID.
                # A more complex system could create a separate ID.
                field["name"] = new_name
                field["@id"] = f"{rs['@id']}/{new_name.lower().replace(' ', '_')}"

    # 4. Apply Profile: Handle descriptions
    if not profile.get("include_descriptions", True):
        croissant_body["description"] = "A minimally described dataset."
        for rs in croissant_body["recordSet"]:
            rs.pop("description", None)
            for field in rs.get("field", []):
                field.pop("description", None)

    # 5. Apply Profile: Strip unwanted extensions
    allowed_prefixes = profile.get("extensions_to_keep", [])
    # Always allow schema.org prefixes like "sc:" and our base context "cr:"
    allowed_prefixes.extend(["sc:", "cr:", "name", "description", "@", "url", "license", "distribution", "recordSet", "field", "source"])
    _strip_unwanted_keys(croissant_body, allowed_prefixes)

    # 6. Finalize top-level metadata
    croissant_body["name"] = f"Mocked Fingerprint - {profile['name']}"
    croissant_body["description"] = croissant_body.get("description") or f"A mocked Croissant fingerprint for the '{profile['name']}' profile."

    return fp_mocked

def generate_mock_data(node: Any) -> Any:
    """Recursively traverses the template and replaces values with mocked data."""
    if isinstance(node, dict):
        if "stat:statistics" in node:
            stats_template = node["stat:statistics"]
            if "stat:min" in stats_template or "stat:mean" in stats_template:
                node["stat:statistics"] = mock_numeric_stats(stats_template)
            else:
                node["stat:statistics"] = mock_categorical_stats(stats_template)
        if "jsd:textDistribution" in node:
            node["jsd:textDistribution"] = mock_jsd_stats()
        if "ex:imageStats" in node:
            node["ex:imageStats"] = mock_image_stats()
        if "ex:annotationStats" in node:
            node["ex:annotationStats"] = mock_annotation_stats()
        if "ex:datasetStats" in node:
            node["ex:datasetStats"] = mock_dataset_stats()
        return {k: generate_mock_data(v) for k, v in node.items()}
    if isinstance(node, list):
        return [generate_mock_data(item) for item in node]
    return node

# --- UNCHANGED: API Interaction and File I/O ---
def get_access_token() -> Optional[str]:
    payload = {
        "client_id": API_CONFIG["KEYCLOAK_CLIENT_ID"],
        "grant_type": "password",
        "username": API_CONFIG["ADMIN_USERNAME"],
        "password": API_CONFIG["ADMIN_PASSWORD"],
    }
    try:
        r = requests.post(API_CONFIG["KEYCLOAK_TOKEN_URL"], data=payload, timeout=10)
        r.raise_for_status()
        return r.json().get("access_token")
    except requests.RequestException as e:
        print(f"Auth error: {e}")
        return None

def post_fingerprint(fp: Dict, token: str) -> bool:
    url = f"{API_CONFIG['API_BASE_URL']}/api/organizations/{API_CONFIG['ORGANIZATION_ID']}/datasets/{API_CONFIG['DATASET_ID']}/fingerprints"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=fp, timeout=15)
        r.raise_for_status()
        print(f"    ✓ POST successful. Response: {r.status_code}")
        return True
    except requests.RequestException as e:
        status = e.response.status_code if hasattr(e, "response") and e.response else "?"
        error_body = e.response.text if hasattr(e, "response") and e.response else "No response body."
        print(f"    ✗ POST failed ({status}): {e}\n      Response Body: {error_body}")
        return False
    
def read_template(p: Path) -> Dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save_fingerprint(fp: Dict, filename: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / filename, "w", encoding="utf-8") as f:
        json.dump(fp, f, indent=2)
    print(f"    ✓ Saved: {outdir / filename}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--count", type=int, default=20, help="Number of mocks to generate.")
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTDIR) 
    ap.add_argument("-t", "--template-file", type=Path, default=DEFAULT_TPL)
    ap.add_argument("--send", action="store_true", help="Send generated fingerprints to the API.")
    args = ap.parse_args()

    master = read_template(args.template_file)
    # Create a weighted list of profiles to choose from
    weighted_profiles = [p for p in FINGERPRINT_PROFILES for _ in range(p["weight"])]

    token = get_access_token() if args.send else None
    if args.send and not token:
        print("Unable to fetch token ─ mocks will be generated locally only.")
        args.send = False

    print(f"Generating {args.count} mock fingerprint(s) from {args.template_file.name}")
    for i in range(1, args.count + 1):
        prof = random.choice(weighted_profiles)
        print(f"  • ({i}/{args.count}) profile: {prof['name']}")
        
        # The main creation logic is now in this function
        fp = create_fingerprint(master, prof)
        
        # Assign a unique datasetId for the outer wrapper
        fp["data"]["datasetId"] = f"mock-dataset-id-{fake.uuid4()}"
        
        fname = f"mock_{prof['name']}_{i}.json"
        save_fingerprint(fp, fname, args.output_dir)

        if args.send and token:
            post_fingerprint(fp, token)

    print(f"\nSuccessfully generated {args.count} mocks in directory: {args.output_dir}")

if __name__ == "__main__":
    main()