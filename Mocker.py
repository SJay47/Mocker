from __future__ import annotations

import argparse, json, random
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from faker import Faker

# ---------------------------------------------------------------------------
#  CONSTANTS AND CONFIG
# ---------------------------------------------------------------------------

ROOT_DIR       = Path(__file__).resolve().parent
DEFAULT_TPL    = ROOT_DIR / "templates" / "master_fingerprint_template.json"
DEFAULT_OUTDIR = ROOT_DIR / "mock_outputs"

API_CONFIG = {
    "API_BASE_URL":        "http://localhost",
    "KEYCLOAK_TOKEN_URL":  "http://localhost:18080/realms/primecare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID":  "primecare-frontend-postman",
    "ADMIN_USERNAME":      "alice@demo.com",
    "ADMIN_PASSWORD":      "q",
    "ORGANIZATION_ID":     "c0b68ef3-2327-4b2c-bc70-71e11663f1cd",
    "DATASET_ID":          "66912ec9-9e1e-44e9-b3f5-1aefc4dfba18",
}

fake = Faker()
random.seed()
Faker.seed()

FINGERPRINT_PROFILES = [
    {"name": "Rich Multi-Modal",        "record_set_ids": ["patient_demographics", "vital_signs", "clinical_notes", "medical_images"], "weight": 15},
    {"name": "Classic Tabular",         "record_set_ids": ["patient_demographics", "vital_signs"],                                       "weight": 30},
    {"name": "Imaging Center Specialist","record_set_ids": ["medical_images"],                                                            "weight": 20},
    {"name": "Text-Heavy Unstructured", "record_set_ids": ["patient_demographics", "clinical_notes"],                                    "weight": 20},
    {"name": "Incomplete Minimalist",   "record_set_ids": ["vital_signs"],                          "is_incomplete": True,              "weight": 15},
]

# ---------------------------------------------------------------------------
#  MOCK HELPERS
# ---------------------------------------------------------------------------

def rand_float(lo: float, hi: float, digits: int = 2) -> float:
    return round(random.uniform(lo, hi), digits)

def mock_statistics(k: str) -> Any:
    if k in ("min", "quartile_1", "percentile_5"):        return rand_float(10, 40)
    if k in ("median", "mean"):                           return rand_float(40, 80)
    if k in ("max", "quartile_3", "percentile_95"):       return rand_float(80, 150)
    if k == "stdDev":                                     return rand_float(5, 20)
    if k in ("unique_count", "missing_count", "mode_frequency"): return fake.random_int(0, 5000)
    if k in ("skewness", "kurtosis"):                     return rand_float(-1, 1, 2)
    if k == "entropy":                                    return rand_float(1, 4, 4)
    if k == "counts":                                     return [fake.random_int(100, 3000) for _ in range(8)]
    return None

def mock_image_stats() -> dict:
    min_w, max_w = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    min_h, max_h = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    return {
        "ex:numImages": fake.random_int(500, 10000),
        "ex:imageDimensions": {
            "ex:minWidth": min_w,  "ex:maxWidth": max_w,
            "ex:minHeight": min_h, "ex:maxHeight": max_h,
            "ex:avgWidth": (min_w + max_w) // 2,
            "ex:avgHeight": (min_h + max_h) // 2,
            "ex:aspectRatioDistribution": random.choice(["1:1", "4:3", "16:9"]),
        },
        "ex:colorMode": random.choice(["grayscale", "RGB"]),
        "ex:channels": 1 if random.choice([True, False]) else 3,
        "ex:fileSizeBytes": {
            "ex:avg": fake.random_int(100000, 500000),
            "ex:min": fake.random_int(10000, 100000),
            "ex:max": fake.random_int(500000, 2000000),
        },
        "ex:modality": random.choice(["X-ray", "MRI", "CT Scan", "Microscopy"]),
    }

def mock_annotation_stats() -> dict:
    classes = sorted({*fake.words(nb=random.randint(2, 8),
                                  ext_word_list=["nodule","fracture","tumor","device",
                                                 "lesion","opacity","cyst","inflammation"])})
    return {
        "ex:numAnnotations": fake.random_int(1000, 50000),
        "ex:numClasses": len(classes),
        "ex:classes": classes,
        "ex:objectsPerImage": {
            "ex:min": fake.random_int(0, 1),
            "ex:max": fake.random_int(2, 10),
            "ex:avg": rand_float(1, 5, 2),
            "ex:median": fake.random_int(1, 4),
        },
        "ex:boundingBoxStats": {
            "ex:avgRelativeWidth":  rand_float(0.1, 0.5, 2),
            "ex:avgRelativeHeight": rand_float(0.1, 0.5, 2),
            "ex:avgAspectRatio":    rand_float(0.5, 1.5, 2),
            "ex:relativeAreaDistribution": f"beta({fake.random_int(2,5)},{fake.random_int(2,5)})",
            "ex:shapeNotes": random.choice(["rectangular", "mostly rectangular", "varied"]),
        },
    }

def _norm(v): s = sum(v) or 1; return [round(x / s, 6) for x in v]

def mock_jsd_stats() -> dict:
    toks  = [fake.word() for _ in range(5)]
    probs = _norm([random.random() for _ in toks])
    return {
        "@type": "TextDistribution",
        "total_records_analyzed": fake.random_int(500, 10000),
        "missing_count": fake.random_int(0, 200),
        "language": "en",
        "text_summary_stats": {
            "mean_tokens_per_record": rand_float(50, 200, 1),
            "median_tokens_per_record": fake.random_int(40, 180),
            "total_unique_tokens": fake.random_int(5000, 25000),
        },
        "vocabulary_size": len(toks),
        "top_k_tokens": [{"token": t, "frequency": p} for t, p in zip(toks, probs)],
        "token_probability_vector": probs,
    }

def generate_mock_data(node: Any, *, strip: bool = False) -> Any:
    if isinstance(node, dict):
        if "ex:imageStats" in node:
            node["ex:imageStats"] = {} if strip else mock_image_stats()
        if "ex:annotationStats" in node:
            node["ex:annotationStats"] = {} if strip else mock_annotation_stats()
        out: Dict[str, Any] = {}
        for k, v in node.items():
            if k == "statistics" and isinstance(v, dict):
                if strip: continue
                new_stats: Dict[str, Any] = {}
                for sk, sv in v.items():
                    if isinstance(sv, (int, float)) or sk == "counts":
                        new_stats[sk] = mock_statistics(sk)
                    elif sk == "category_frequencies" and isinstance(sv, dict):
                        new_stats[sk] = {ck: fake.random_int(100, 3000) for ck in sv}
                    elif isinstance(sv, dict):
                        new_stats[sk] = generate_mock_data(sv, strip=strip)
                    else:
                        new_stats[sk] = sv
                out[k] = new_stats
            elif k == "jsd:textDistribution":
                if not strip:
                    out[k] = mock_jsd_stats()
            else:
                out[k] = generate_mock_data(v, strip=strip)
        return out
    if isinstance(node, list):
        return [generate_mock_data(i, strip=strip) for i in node]
    return node

def create_fingerprint(tpl: Dict, profile: Dict) -> Dict:
    fp = deepcopy(tpl)
    rs_all = fp["data"]["rawFingerprintJson"]["recordSet"]
    fp["data"]["rawFingerprintJson"]["recordSet"] = [rs for rs in rs_all if rs["@id"] in profile["record_set_ids"]]
    fp["data"]["rawFingerprintJson"]["name"] = f"Mocked Fingerprint - {profile['name']}"
    return generate_mock_data(fp, strip=profile.get("is_incomplete", False))

# ---------------------------------------------------------------------------
#  API HELPERS
# ---------------------------------------------------------------------------

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
        return True
    except requests.RequestException as e:
        status = e.response.status_code if hasattr(e, "response") and e.response else "?"
        print(f"POST failed ({status}): {e}")
        return False

# ---------------------------------------------------------------------------
#  IO HELPERS
# ---------------------------------------------------------------------------

def read_template(p: Path) -> Dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save(fp: Dict, fname: str, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / fname, "w", encoding="utf-8") as f:
        json.dump(fp, f, indent=2)

# ---------------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--count", type=int, default=10)
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("-t", "--template-file", type=Path, default=DEFAULT_TPL)
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    master = read_template(args.template_file)
    profiles = [p for p in FINGERPRINT_PROFILES for _ in range(p["weight"])]

    token = get_access_token() if args.send else None
    if args.send and not token:
        print("Unable to fetch token ─ mocks will be generated locally only.")

    print(f"Generating {args.count} mock fingerprint(s) from {args.template_file}")
    for i in range(1, args.count + 1):
        prof = random.choice(profiles)
        print(f"  • ({i}/{args.count}) profile: {prof['name']}")
        fp = create_fingerprint(master, prof)
        fp["data"]["datasetId"] = API_CONFIG["DATASET_ID"]
        fname = f"mock_{prof['name'].replace(' ', '_')}_{i}.json"
        save(fp, fname, args.output_dir)

        if token:
            ok = post_fingerprint(fp, token)
            msg = "✓ sent" if ok else "✗ send failed"
            print(f"    {msg}")

    print(f"Mocks saved to {args.output_dir}")

if __name__ == "__main__":
    main()
