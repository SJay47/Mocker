from __future__ import annotations

import argparse
import copy
import json
import random
import string
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from faker import Faker

fake = Faker()

# ---------------------------------------------------------------------------
# CONFIGURATION (unchanged)
# ---------------------------------------------------------------------------
API_CONFIG = {
    "API_BASE_URL": "https://dev-ppfl-api.asclepyus.com",
    "KEYCLOAK_TOKEN_URL": "https://dev-ppfl-auth.asclepyus.com/keycloak/admin/realms/PrimeCare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID": "public-dev-ppfl-api-swagger",
    "ADMIN_USERNAME": "alice@demo.com",
    "ADMIN_PASSWORD": "123",
    "ORGANIZATION_ID": "23a41582-ba93-4ea0-8ec9-be45022c89e1",
    "DATASET_ID": "2df73cb6-66f3-4d6d-9232-77fc32fe652a",
}

# ---------------------------------------------------------------------------
# RANDOM HELPERS
# ---------------------------------------------------------------------------


def _rand_str(k: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=k))


def _random_image_stats() -> Dict[str, Any]:
    width = random.randint(256, 4096)
    height = random.randint(256, 4096)
    return {
        "ex:numImages": random.randint(100, 10000),
        "ex:imageDimensions": {
            "ex:minWidth": random.randint(64, width // 2),
            "ex:maxWidth": width,
            "ex:minHeight": random.randint(64, height // 2),
            "ex:maxHeight": height,
            "ex:avgWidth": width // 2,
            "ex:avgHeight": height // 2,
            "ex:aspectRatioDistribution": ";".join(
                str(round(random.uniform(0.5, 2.0), 2)) for _ in range(5)
            ),
        },
        "ex:colorMode": random.choice(["RGB", "BGR", "Grayscale"]),
        "ex:channels": random.choice([1, 3]),
        "ex:fileSizeBytes": {
            "ex:avg": random.randint(10_000, 500_000),
            "ex:min": random.randint(1_000, 9_999),
            "ex:max": random.randint(500_001, 5_000_000),
        },
        "ex:modality": random.choice(["xray", "photo", "microscopy", "CT"]),
    }


def _random_annotation_stats() -> Dict[str, Any]:
    num_classes = random.randint(2, 20)
    classes = [fake.word() for _ in range(num_classes)]
    return {
        "ex:numAnnotations": random.randint(5_000, 100_000),
        "ex:numClasses": num_classes,
        "ex:classes": classes,
        "ex:objectsPerImage": {
            "ex:min": random.randint(0, 1),
            "ex:max": random.randint(5, 20),
            "ex:avg": round(random.uniform(1, 10), 2),
            "ex:median": random.randint(1, 5),
        },
        "ex:boundingBoxStats": {
            "ex:avgRelativeWidth": round(random.uniform(0.05, 0.5), 3),
            "ex:avgRelativeHeight": round(random.uniform(0.05, 0.5), 3),
            "ex:avgAspectRatio": round(random.uniform(0.5, 3.0), 2),
            "ex:relativeAreaDistribution": ";".join(
                str(round(random.uniform(0.01, 0.9), 3)) for _ in range(5)
            ),
            "ex:shapeNotes": random.choice(["mostly-square", "elongated", "mixed"]),
        },
    }


# ---------------------------------------------------------------------------
# STATISTICS MOCKER (unchanged from v1)
# ---------------------------------------------------------------------------


def custom_generate(data: Any) -> Any:
    if isinstance(data, dict):
        new_data: Dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() == "statistics" and isinstance(value, dict):
                stats_data = value.copy()
                new_stats = stats_data.copy()

                if "min" in stats_data:
                    is_float = isinstance(stats_data["min"], float)
                    min_val = (
                        fake.pyfloat(min_value=10, max_value=40, right_digits=2)
                        if is_float
                        else random.randint(10, 40)
                    )
                    max_val = (
                        fake.pyfloat(
                            min_value=min_val + 50, max_value=150, right_digits=2
                        )
                        if is_float
                        else random.randint(min_val + 50, 150)
                    )
                    p5 = random.uniform(min_val, min_val + (max_val - min_val) * 0.1)
                    q1 = random.uniform(p5, min_val + (max_val - min_val) * 0.3)
                    median = random.uniform(q1, min_val + (max_val - min_val) * 0.6)
                    q3 = random.uniform(median, max_val * 0.9)
                    p95 = random.uniform(q3, max_val)
                    mean_val = random.uniform(q1, q3)

                    for k in new_stats:
                        if k in {"min", "max", "mean", "median"}:
                            val_map = {
                                "min": min_val,
                                "max": max_val,
                                "mean": mean_val,
                                "median": median,
                            }[k]
                            new_stats[k] = (
                                round(val_map, 2) if is_float else int(val_map)
                            )
                        elif k in {
                            "quartile_1",
                            "quartile_3",
                            "percentile_5",
                            "percentile_95",
                        }:
                            map2 = {
                                "quartile_1": q1,
                                "quartile_3": q3,
                                "percentile_5": p5,
                                "percentile_95": p95,
                            }[k]
                            new_stats[k] = round(map2, 2) if is_float else int(map2)
                        elif k == "stdDev":
                            new_stats[k] = round(random.uniform(5, 20), 2)
                        elif k in {"unique_count", "missing_count"}:
                            new_stats[k] = random.randint(0, 100)
                        elif k in {"skewness", "kurtosis"}:
                            new_stats[k] = round(random.uniform(-1, 1), 2)
                        elif k == "histogram" and isinstance(stats_data[k], dict):
                            bins = stats_data[k].get("bins", [])
                            new_stats[k]["counts"] = [
                                random.randint(100, 2000) for _ in bins
                            ]

                elif "mode" in stats_data:
                    for k in new_stats:
                        if k in {"unique_count", "missing_count", "mode_frequency"}:
                            new_stats[k] = random.randint(0, 5000)
                        elif k == "entropy":
                            new_stats[k] = round(random.uniform(0.5, 3.0), 2)
                        elif k == "category_frequencies" and isinstance(
                            stats_data[k], dict
                        ):
                            new_stats[k] = {
                                cat: random.randint(100, 3000) for cat in stats_data[k]
                            }

                new_data[key] = new_stats
            else:
                new_data[key] = custom_generate(value)
        return new_data

    if isinstance(data, list):
        return [custom_generate(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# BUILD FINGERPRINT
# ---------------------------------------------------------------------------


def build_fingerprint(
    template: Dict[str, Any], *, record_count: int, extensions: List[str]
) -> Dict[str, Any]:
    fp = copy.deepcopy(template)

    # Replace recordCount in *all* recordSets (template may have many after earlier cloning)
    for rs in fp["data"]["rawFingerprintJson"].get("recordSet", []):
        rs["recordCount"] = record_count

    root_json = fp["data"]["rawFingerprintJson"]
    # Manage image extension
    if "image" in extensions:
        root_json["ex:imageStats"] = _random_image_stats()
    else:
        root_json.pop("ex:imageStats", None)
    # Manage annotation extension
    if "annotation" in extensions:
        root_json["ex:annotationStats"] = _random_annotation_stats()
    else:
        root_json.pop("ex:annotationStats", None)
    # textual / stats handled implicitly

    fp = custom_generate(fp)
    fp["data"]["datasetId"] = API_CONFIG["DATASET_ID"]
    return fp


# ---------------------------------------------------------------------------
# API & FILE IO
# ---------------------------------------------------------------------------


def save_fingerprint(fp: Dict[str, Any], filename: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(fp, f, indent=2)
    return path


def read_template(tpl_path: Path) -> Dict[str, Any]:
    with tpl_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_token() -> Optional[str]:
    payload = {
        "client_id": API_CONFIG["KEYCLOAK_CLIENT_ID"],
        "grant_type": "password",
        "username": API_CONFIG["ADMIN_USERNAME"],
        "password": API_CONFIG["ADMIN_PASSWORD"],
    }
    try:
        r = requests.post(API_CONFIG["KEYCLOAK_TOKEN_URL"], data=payload, timeout=10)
        r.raise_for_status()
        return r.json()["access_token"]
    except requests.RequestException as exc:
        print(f"Auth error: {exc}")
        return None


def post_fp(fp: Dict[str, Any], token: str) -> bool:
    url = f"{API_CONFIG['API_BASE_URL']}/api/organizations/{API_CONFIG['ORGANIZATION_ID']}/datasets/{API_CONFIG['DATASET_ID']}/fingerprints"
    try:
        r = requests.post(
            url,
            json=fp,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        r.raise_for_status()
        return True
    except requests.RequestException as exc:
        print(f"POST error: {exc}")
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="Generate & optionally POST Croissant fingerprints (minimal CLI)"
    )
    p.add_argument(
        "--count",
        "-c",
        "--c",
        type=int,
        default=10,
        help="Number of fingerprints to generate per template",
    )
    p.add_argument(
        "--send", "-s", action="store_true", help="POST generated fingerprints to API"
    )
    p.add_argument(
        "--templates-dir",
        "-t",
        default="templates",
        help="Directory with template JSON files",
    )
    p.add_argument(
        "--output-dir",
        "-o",
        default="mock_fingerprints",
        help="Directory to save generated mocks",
    )
    # Advanced (optional) overrides
    p.add_argument(
        "--record-count",
        "--rc",
        "-r",
        type=int,
        help="Force recordCount for all fingerprints (skip random)",
    )
    p.add_argument(
        "--extensions",
        "-e",
        type=str,
        help="Force extension list e.g. stats,image,annotation",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main():
    args = parse_args()
    templates = list(Path(args.templates_dir).glob("*.json"))
    if not templates:
        print(f"No templates found in {args.templates_dir}")
        return

    token = get_token() if args.send else None
    if args.send and not token:
        print("Couldn't retrieve auth token – running offline only")

    EXTENSION_CHOICES = [
        ["stats", "image", "annotation", "textual"],
        ["stats", "image"],
        ["textual", "image", "annotation"],
        ["stats", "image", "annotation"],
    ]

    for tpl in templates:
        base_tpl = read_template(tpl)
        for i in range(args.count):
            # Decide recordCount & extension bundle for this fingerprint
            record_count = (
                args.record_count
                if args.record_count is not None
                else random.randint(1, 15)
            )
            if args.extensions:
                extensions = [
                    e.strip() for e in args.extensions.split(",") if e.strip()
                ]
            else:
                extensions = random.choice(EXTENSION_CHOICES)

            fp = build_fingerprint(
                base_tpl, record_count=record_count, extensions=extensions
            )
            fname = f"mock_{tpl.stem}_{i + 1:03d}.json"
            path = save_fingerprint(fp, fname, Path(args.output_dir))
            print(f"Saved {path}")
            if token and post_fp(fp, token):
                print("  -> Sent ✓")

    print("Done.")


if __name__ == "__main__":
    main()
