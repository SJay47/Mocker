from __future__ import annotations

import argparse
import json
import random
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from faker import Faker

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TPL = ROOT_DIR / "templates" / "master_fingerprint_template.json" 
DEFAULT_OUTDIR = ROOT_DIR / "mock_outputs"


API_CONFIG = {
    "API_BASE_URL": "https://dev-ppfl-api.asclepyus.com",
    "KEYCLOAK_TOKEN_URL": "https://dev-ppfl-auth.asclepyus.com/keycloak/admin/realms/PrimeCare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID": "public-dev-ppfl-api-swagger",
    "ADMIN_USERNAME": "alice@demo.com",
    "ADMIN_PASSWORD": "123",
    "ORGANIZATION_ID": "458df882-affe-49c1-9bb5-8cab59331f93",
    "DATASET_ID": "0a6a4f35-45b5-414d-8483-f7440b331b97"
}

fake = Faker()
random.seed()
Faker.seed()


FINGERPRINT_PROFILES = [
    {"name": "Rich_Multi-Modal",        "record_set_ids": ["patient_demographics", "vital_signs", "clinical_notes", "medical_images"], "weight": 15},
    {"name": "Classic_Tabular",         "record_set_ids": ["patient_demographics", "vital_signs"],                                       "weight": 30},
    {"name": "Imaging_Center_Specialist","record_set_ids": ["medical_images"],                                                            "weight": 20},
    {"name": "Text_Heavy_Unstructured", "record_set_ids": ["patient_demographics", "clinical_notes"],                                    "weight": 20},
    {"name": "Incomplete_Minimalist",   "record_set_ids": ["vital_signs"],                          "is_incomplete": True,              "weight": 15},
]

def rand_float(lo: float, hi: float, digits: int = 2) -> float:
    return round(random.uniform(lo, hi), digits)

def _norm_dist(v):
    s = sum(v) or 1
    return [round(x / s, 6) for x in v]

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
    """
    Mocks statistics for a categorical field, preserving the category names
    defined in the template and only mocking their values.
    """
    stats = {"@type": "stat:Statistics"}
    category_template = template.get("stat:category_frequencies", {})
    original_categories = list(category_template.keys())

    if "stat:unique_count" in template:
        stats["stat:unique_count"] = len(original_categories)

    if "stat:missing_count" in template:
        stats["stat:missing_count"] = fake.random_int(0, 500)

    if "stat:mode" in template and original_categories:
        stats["stat:mode"] = random.choice(original_categories)

    if "stat:mode_frequency" in template:
        stats["stat:mode_frequency"] = fake.random_int(1000, 5000)

    if "stat:entropy" in template:
        stats["stat:entropy"] = rand_float(1, 4)

    if original_categories:
        stats["stat:category_frequencies"] = {
            category: fake.random_int(100, 3000)
            for category in original_categories
        }

    return stats

def mock_image_stats() -> dict:
    min_w, max_w = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    min_h, max_h = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    return {
        "@type": "ex:ImageStatistics",
        "ex:numImages": fake.random_int(500, 10000),
        "ex:imageDimensions": {"ex:minWidth": min_w, "ex:maxWidth": max_w, "ex:minHeight": min_h, "ex:maxHeight": max_h},
        "ex:colorMode": random.choice(["grayscale", "RGB"]),
        "ex:modality": random.choice(["X-ray", "MRI", "CT Scan"]),
    }

def mock_annotation_stats() -> dict:
    classes = sorted({*fake.words(nb=random.randint(2, 8), ext_word_list=["nodule", "fracture", "tumor"])})
    return {
        "@type": "ex:AnnotationStatistics",
        "ex:numAnnotations": fake.random_int(1000, 50000),
        "ex:numClasses": len(classes),
        "ex:classes": classes,
        "ex:objectsPerImage": {"ex:avg": rand_float(1, 5, 2), "ex:median": fake.random_int(1, 4)},
        "ex:boundingBoxStats": {"ex:avgRelativeWidth": rand_float(0.1, 0.5), "ex:avgRelativeHeight": rand_float(0.1, 0.5)},
    }

def mock_jsd_stats() -> dict:
    tokens = [fake.word() for _ in range(5)]
    probs = _norm_dist([random.random() for _ in tokens])
    return {
        "@type": "jsd:TextDistribution",
        "jsd:total_records_analyzed": fake.random_int(500, 10000),
        "jsd:language": "en",
        "jsd:vocabulary_size": len(tokens),
        "jsd:top_k_tokens": [{"jsd:token": t, "jsd:frequency": p} for t, p in zip(tokens, probs)],
        "jsd:token_probability_vector": probs,
    }

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

def create_fingerprint(template: Dict, profile: Dict) -> Dict:
    """Creates a single mocked fingerprint based on a profile."""
    fp_mocked = generate_mock_data(deepcopy(template))
    croissant_body = fp_mocked["data"]["rawFingerprintJson"]
    all_record_sets = croissant_body["recordSet"]
    profiled_record_sets = [rs for rs in all_record_sets if rs["@id"] in profile["record_set_ids"]]
    croissant_body["recordSet"] = profiled_record_sets
    croissant_body["name"] = f"Mocked Fingerprint - {profile['name']}"
    croissant_body["description"] = f"A mocked Croissant fingerprint for the '{profile['name']}' profile."
    if "medical_images" in profile["record_set_ids"]:
        if not any(d["@id"] == "images-zip" for d in croissant_body["distribution"]):
            croissant_body["distribution"].append({
              "@type": "cr:FileObject",
              "@id": "images-zip",
              "name": "medical_images.zip",
              "contentUrl": f"https://example.com/files/mock_images_{fake.uuid4()}.zip",
              "encodingFormat": "application/zip",
              "sha256": fake.sha256()
            })

        for rs in croissant_body["recordSet"]:
            if rs["@id"] == "medical_images":
                rs["field"] = [{
                  "@id": "medical_images/image",
                  "@type": "cr:Field",
                  "name": "Image",
                  "dataType": "sc:ImageObject",
                  "source": {
                    "fileSet": {
                      "@id": "image-files",
                      "containedIn": { "@id": "images-zip" },
                      "includes": "*.dcm"
                    },
                    "extract": { "fileProperty": "content" }
                  }
                }]
                break

    if profile.get("is_incomplete", False):
        for rs in croissant_body["recordSet"]:
            for field in rs.get("field", []):
                if "stat:statistics" in field:
                    del field["stat:statistics"]

    return fp_mocked

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

def read_json_template(filepath: Path) -> Dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_fingerprint(fp: Dict, filename: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / filename, "w", encoding="utf-8") as f:
        json.dump(fp, f, indent=2)
    print(f"    ✓ Saved: {outdir / filename}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--count", type=int, default=10)
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTDIR) 
    ap.add_argument("-t", "--template-file", type=Path, default=DEFAULT_TPL)
    ap.add_argument("--send", action="store_true", help="Send generated fingerprints to the API.")
    args = ap.parse_args()

    master = read_template(args.template_file)
    profiles = [p for p in FINGERPRINT_PROFILES for _ in range(p["weight"])]

    token = get_access_token() if args.send else None
    if args.send and not token:
        print("Unable to fetch token ─ mocks will be generated locally only.")
        args.send = False

    print(f"Generating {args.count} mock fingerprint(s) from {args.template_file}")
    for i in range(1, args.count + 1):
        prof = random.choice(profiles)
        print(f"  • ({i}/{args.count}) profile: {prof['name']}")
        fp = create_fingerprint(master, prof)
        
        fp["data"]["datasetId"] = f"mock-dataset-id-{i}"
        
        fname = f"mock_{prof['name'].replace(' ', '_')}_{i}.json"
        save_fingerprint(fp, fname, args.output_dir)

        if args.send and token:
            post_fingerprint(fp, token)

    print(f"\nSuccessfully generated {args.count} mocks in directory: {args.output_dir}")

if __name__ == "__main__":
    main()