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

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_TPL = ROOT_DIR / "templates" / "master_fingerprint_template.json"
DEFAULT_OUTDIR = ROOT_DIR / "mock_outputs"

API_CONFIG = {
    "API_BASE_URL": "http://api.primecare.local",
    "KEYCLOAK_TOKEN_URL": "http://auth.primecare.local:18080/realms/primecare/protocol/openid-connect/token",
    "KEYCLOAK_CLIENT_ID": "public-dev-ppfl-api-swagger",
    "ADMIN_USERNAME": "alice@demo.com",
    "ADMIN_PASSWORD": "q",
    "ORGANIZATION_ID": "6770514c-b074-4b85-80c5-924b5ef77abb",
    "DATASET_ID": "ad229b50-1a4f-47f8-b15a-5e34a12681d2",
    "CREATE_ORGANIZATION_ENDPOINT": "/api/organizations",
    "CREATE_DATASET_ENDPOINT_TEMPLATE": "/api/organizations/{org_id}/datasets",
    "CREATE_FINGERPRINT_ENDPOINT_TEMPLATE": "/api/organizations/{org_id}/datasets/{dataset_id}/fingerprints"
}


fake = Faker()
random.seed()
Faker.seed()

MEDICAL_DOMAINS = [
    {
        "name": "Cardiology",
        "description": "Dataset focusing on cardiovascular health, including patient vitals, lab results for heart conditions, and cardiac imaging reports.",
        "jsd_tokens": ["cardiac", "artery", "atrial", "ventricle", "aortic", "stenosis", "echocardiogram", "hypertension", "cholesterol", "stent", "infarction", "fibrillation"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "Patient Age", "age_at_scan"], "description": "Patient's age at the time of cardiac assessment.", "params": {"min": 40, "max": 95}},
            "patient_demographics/patient_blood_type": {"variants": ["blood_type", "Blood Group", "patient_blood_group"], "description": "Patient's blood group, relevant for surgical procedures."},
            "vital_signs/bmi": {"variants": ["BMI", "body_mass_index"], "description": "Body Mass Index, a key risk factor for heart disease.", "params": {"min": 18, "max": 45}},
            "vital_signs/blood_pressure": {"variants": ["blood_pressure", "BP", "Systolic/Diastolic"], "description": "Blood pressure reading (e.g., 120/80 mmHg).", "params": {"categories": ["120/80", "130/85", "140/90", "110/70"]}},
            "lab_results/cholesterol": {"variants": ["cholesterol", "Total Cholesterol", "CHOL_Total"], "description": "Total cholesterol level in mg/dL.", "params": {"min": 150, "max": 300}},
            "clinical_notes/notes": {"variants": ["Cardiology Notes", "consultation_report", "ECHO_notes"], "description": "Clinical notes from cardiology consultations and echocardiograms."},
            "medical_condition/diagnosis": {"variants": ["diagnosis", "Condition", "Primary Cardiac Diagnosis"], "description": "Primary diagnosis related to cardiovascular disease.", "params": {"categories": ["Hypertension", "Coronary Artery Disease", "Myocardial Infarction", "Heart Failure", "Arrhythmia"]}},
            "medical_images/modality": "Echocardiogram"
        }
    },
    {
        "name": "Neurology",
        "description": "A collection of neurological patient data, including demographics, cognitive assessments, and brain imaging scans like MRIs.",
        "jsd_tokens": ["neuron", "synapse", "cognitive", "mri", "lesion", "seizure", "alzheimer", "parkinson", "stroke", "axon", "neuropathy", "cortical"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "Age at Onset", "patient_age_neuro"], "description": "Patient's age at the onset of neurological symptoms.", "params": {"min": 25, "max": 90}},
            "cognitive_assessment/moca_score": {"variants": ["MoCA Score", "Cognitive Score", "Montreal Cognitive Assessment"], "description": "Score from the Montreal Cognitive Assessment (MoCA), ranging from 0 to 30.", "params": {"min": 5, "max": 30}},
            "clinical_notes/notes": {"variants": ["Neurology Progress Notes", "mri_findings_summary", "Clinical Observations"], "description": "Detailed notes on patient's neurological status and MRI findings."},
            "medical_condition/diagnosis": {"variants": ["diagnosis", "Neurological Condition", "Final Diagnosis"], "description": "Primary neurological diagnosis.", "params": {"categories": ["Alzheimer's Disease", "Parkinson's Disease", "Multiple Sclerosis", "Stroke", "Epilepsy"]}},
            "medical_images/modality": "MRI"
        }
    },
    {
        "name": "Oncology",
        "description": "Dataset containing information on cancer patients, including tumor characteristics, treatment protocols, and genetic markers.",
        "jsd_tokens": ["tumor", "cell", "chemotherapy", "lesion", "radiation", "stage", "grade", "biopsy", "metastatic", "carcinoma", "adenocarcinoma", "lymphoma"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age_at_diagnosis", "Age", "patient_age"], "description": "Age of the patient at the time of cancer diagnosis."},
            "tumor_markers/tumor_size": {"variants": ["Tumor Size (cm)", "tumor_diameter", "Lesion Size"], "description": "The largest dimension of the primary tumor in centimeters.", "params": {"min": 0.5, "max": 15}},
            "tumor_markers/cancer_stage": {"variants": ["Cancer Stage", "Stage", "TNM Stage"], "description": "The stage of the cancer at diagnosis.", "params": {"categories": ["Stage I", "Stage II", "Stage III", "Stage IV"]}},
            "clinical_notes/notes": {"variants": ["Oncology Report", "biopsy_results", "treatment_summary"], "description": "Notes detailing biopsy results, pathology, and treatment history."},
            "medical_condition/diagnosis": {"variants": ["Cancer Type", "Histology", "Oncological Diagnosis"], "description": "The specific type of cancer.", "params": {"categories": ["Breast Cancer", "Lung Cancer", "Prostate Cancer", "Colorectal Cancer", "Melanoma"]}},
            "medical_images/modality": "PET-CT"
        }
    },
    {
        "name": "Pulmonology",
        "description": "Focuses on respiratory diseases, with data on lung function tests, patient-reported outcomes, and chest X-rays.",
        "jsd_tokens": ["respiratory", "lung", "bronchial", "fev1", "fvc", "spirometry", "copd", "asthma", "pleural", "inhaler", "pulmonary", "ventilation"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "patient_age"], "description": "Patient's age."},
            "lung_function/fev1": {"variants": ["FEV1", "Forced Expiratory Volume 1s", "pulmonary_fev1"], "description": "Forced Expiratory Volume in 1 second, a measure of lung function.", "params": {"min": 1, "max": 5}},
            "lung_function/fvc": {"variants": ["FVC", "Forced Vital Capacity", "pulmonary_fvc"], "description": "Forced Vital Capacity, a measure of lung capacity.", "params": {"min": 1, "max": 6}},
            "clinical_notes/notes": {"variants": ["Pulmonology Notes", "chest_xray_report", "Spirometry Notes"], "description": "Clinical notes regarding patient's respiratory health and test results."},
            "medical_condition/diagnosis": {"variants": ["diagnosis", "Respiratory Condition"], "description": "Primary respiratory diagnosis.", "params": {"categories": ["COPD", "Asthma", "Idiopathic Pulmonary Fibrosis", "Pneumonia"]}},
            "medical_images/modality": "X-ray"
        }
    },
    {
        "name": "Gastroenterology",
        "description": "Data related to digestive system disorders, including endoscopy results, lab tests, and patient history.",
        "jsd_tokens": ["gastrointestinal", "endoscopy", "colon", "stomach", "liver", "hepatic", "enzyme", "colitis", "crohns", "ulcer", "biopsy", "polyp"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "patient_age_gi"], "description": "Patient's age at time of consultation."},
            "lab_results/liver_enzymes": {"variants": ["Liver Function Tests", "AST/ALT", "liver_enzymes"], "description": "Key liver enzyme levels (AST/ALT).", "params": {"min": 10, "max": 200}},
            "clinical_notes/notes": {"variants": ["Endoscopy Report", "GI Consult Notes", "pathology_report"], "description": "Detailed findings from gastrointestinal procedures."},
            "medical_condition/diagnosis": {"variants": ["GI Diagnosis", "condition"], "description": "Diagnosis related to the digestive system.", "params": {"categories": ["Crohn's Disease", "Ulcerative Colitis", "IBS", "Gastroesophageal Reflux Disease (GERD)"]}},
            "medical_images/modality": "Endoscopy"
        }
    },
    {
        "name": "Nephrology",
        "description": "Dataset for kidney-related diseases, focusing on renal function tests and patient demographics.",
        "jsd_tokens": ["renal", "kidney", "nephron", "glomerular", "dialysis", "creatinine", "egfr", "ckd", "tubular", "urinalysis", "biopsy", "transplant"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "patient_age"], "description": "Patient's age."},
            "lab_results/creatinine": {"variants": ["Serum Creatinine", "Creatinine", "renal_creatinine"], "description": "Serum creatinine level, a marker for kidney function.", "params": {"min": 0.6, "max": 4.0}},
            "lab_results/egfr": {"variants": ["eGFR", "Estimated Glomerular Filtration Rate", "renal_egfr"], "description": "eGFR, a key indicator of kidney health.", "params": {"min": 20, "max": 110}},
            "clinical_notes/notes": {"variants": ["Nephrology Consult", "renal_biopsy_notes"], "description": "Clinical notes from nephrology specialists."},
            "medical_condition/diagnosis": {"variants": ["diagnosis", "Renal Disease"], "description": "Primary diagnosis for kidney condition.", "params": {"categories": ["Chronic Kidney Disease (CKD)", "Acute Kidney Injury (AKI)", "Glomerulonephritis", "Polycystic Kidney Disease"]}},
            "medical_images/modality": "Ultrasound"
        }
    },
    {
        "name": "Endocrinology",
        "description": "Data focusing on endocrine disorders, primarily diabetes, including blood glucose levels and HbA1c measurements.",
        "jsd_tokens": ["endocrine", "hormone", "gland", "diabetes", "glucose", "insulin", "hba1c", "thyroid", "pituitary", "adrenal", "metabolism"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "patient_age_endo"], "description": "Patient's age."},
            "lab_results/hba1c": {"variants": ["HbA1c", "Hemoglobin A1c"], "description": "Glycated hemoglobin (HbA1c), an indicator of long-term glucose control.", "params": {"min": 5.0, "max": 14.0}},
            "lab_results/glucose": {"variants": ["Fasting Glucose", "blood_sugar"], "description": "Fasting blood glucose level.", "params": {"min": 80, "max": 350}},
            "clinical_notes/notes": {"variants": ["Endocrinology Notes", "diabetes_management_plan"], "description": "Notes related to patient's endocrine health and treatment."},
            "medical_condition/diagnosis": {"variants": ["diagnosis", "Endocrine Disorder"], "description": "Primary endocrine diagnosis.", "params": {"categories": ["Type 1 Diabetes", "Type 2 Diabetes", "Hypothyroidism", "Hyperthyroidism"]}},
        }
    },
    {
        "name": "Orthopedics",
        "description": "Dataset of orthopedic cases, including type of injury, surgical procedure details, and post-operative outcomes.",
        "jsd_tokens": ["orthopedic", "bone", "joint", "fracture", "ligament", "tendon", "arthroplasty", "fusion", "xray", "femur", "tibia", "cartilage"],
        "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "age_at_injury"], "description": "Patient's age at the time of injury."},
            "injury_details/body_part": {"variants": ["Affected Body Part", "Injury Location", "body_part"], "description": "Location of the orthopedic injury.", "params": {"categories": ["Knee", "Hip", "Shoulder", "Spine", "Ankle"]}},
            "injury_details/procedure": {"variants": ["Surgical Procedure", "treatment", "ortho_procedure"], "description": "The orthopedic procedure performed.", "params": {"categories": ["Arthroplasty", "ACL Reconstruction", "Spinal Fusion", "Fracture Repair"]}},
            "clinical_notes/notes": {"variants": ["Orthopedic Surgery Notes", "post_op_report", "physio_notes"], "description": "Surgical and post-operative physiotherapy notes."},
            "medical_condition/diagnosis": {"variants": ["injury_type", "Orthopedic Diagnosis"], "description": "Specific type of orthopedic injury or condition.", "params": {"categories": ["Femur Fracture", "ACL Tear", "Rotator Cuff Tear", "Osteoarthritis"]}},
            "medical_images/modality": "X-ray"
        }
    },
    {
        "name": "Infectious Disease",
        "description": "Dataset tracking infectious diseases, including pathogen identification, patient symptoms, and treatment responses.",
        "jsd_tokens": ["infection", "bacteria", "virus", "antibiotic", "culture", "sepsis", "pathogen", "viral_load", "fever", "leukocyte", "resistance"],
         "fields": {
            "patient_demographics/patient_age": {"variants": ["age", "patient_age_infection"], "description": "Patient's age."},
            "lab_results/pathogen": {"variants": ["Pathogen", "Infectious Agent", "culture_result"], "description": "The identified pathogen causing the infection.", "params": {"categories": ["Staphylococcus aureus", "Influenza A", "SARS-CoV-2", "Escherichia coli"]}},
            "clinical_notes/notes": {"variants": ["Infectious Disease Consult", "symptom_log"], "description": "Notes detailing patient symptoms and response to treatment."},
            "medical_condition/diagnosis": {"variants": ["Infection Type", "disease"], "description": "The specific infectious disease diagnosed.", "params": {"categories": ["Influenza", "COVID-19", "Tuberculosis", "Sepsis"]}},
        }
    }
]

FINGERPRINT_PROFILES = [
    {"name": "Rich_MultiModal", "record_set_ids": "all", "extensions_to_keep": ["ex:", "stat:", "jsd:"], "include_descriptions": True, "weight": 10},
    {"name": "Classic_Tabular_With_Stats", "record_set_ids": "non_imaging", "extensions_to_keep": ["stat:"], "include_descriptions": True, "weight": 20},
    {"name": "Imaging_Only", "record_set_ids": ["medical_images"], "extensions_to_keep": ["ex:"], "include_descriptions": True, "weight": 15},
    {"name": "Text_Heavy_With_JSD", "record_set_ids": ["patient_demographics", "clinical_notes", "medical_condition"], "extensions_to_keep": ["jsd:", "stat:"], "include_descriptions": True, "weight": 15},
    {"name": "Abbreviated_Clinical_No_Descriptions", "record_set_ids": "non_imaging", "extensions_to_keep": [], "include_descriptions": False, "weight": 15},
    {"name": "Purely_Descriptive_No_Records", "record_set_ids": [], "extensions_to_keep": [], "include_descriptions": True, "weight": 10},
    {"name": "Minimalist_Tabular", "record_set_ids": ["patient_demographics", "vital_signs", "lab_results"], "extensions_to_keep": [], "include_descriptions": False, "weight": 15},
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

def mock_numeric_stats(template: dict, params: Optional[Dict] = None) -> dict:
    params = params or {}
    stats = {"@type": "stat:Statistics"}
    stats_template_block = template  
    min_val = params.get("min", stats_template_block.get("stat:min", 10))
    max_val = params.get("max", stats_template_block.get("stat:max", 150))

    mean_val = rand_float(min_val, max_val)
    stats["stat:min"] = rand_float(min_val, min_val + (max_val - min_val) * 0.2)
    stats["stat:max"] = rand_float(max_val - (max_val - min_val) * 0.2, max_val)
    stats["stat:mean"] = mean_val
    stats["stat:median"] = mean_val + rand_float(-5, 5)
    stats["stat:stdDev"] = rand_float(5, 20)
    stats["stat:unique_count"] = fake.random_int(50, 100)
    stats["stat:missing_count"] = fake.random_int(0, 500)
    stats["stat:skewness"] = rand_float(-1, 1)
    stats["stat:kurtosis"] = rand_float(-1, 1)
    if "stat:histogram" in stats_template_block:
        num_bins = random.randint(6, 10)
        bins = sorted([rand_float(stats["stat:min"], stats["stat:max"]) for _ in range(num_bins)])
        bins[0] = round(stats["stat:min"], 2)
        bins[-1] = round(stats["stat:max"], 2)
        bins = sorted(list(set(bins)))
        if len(bins) > 1:
            counts = [fake.random_int(100, 3000) for _ in range(len(bins) - 1)]
        else:
            counts = [] 
        stats["stat:histogram"] = {"stat:bins": bins, "stat:counts": counts}
        
    return stats

def mock_categorical_stats(template: dict, params: Optional[Dict] = None) -> dict:
    params = params or {}
    stats = {"@type": "stat:Statistics"}

    if "categories" in params:
        categories = params["categories"]
    else:
        categories = list(template.get("stat:statistics", {}).get("stat:category_frequencies", {}).keys())

    stats["stat:unique_count"] = len(categories)
    stats["stat:missing_count"] = fake.random_int(0, 500)
    if categories:
        stats["stat:mode"] = random.choice(categories)
        stats["stat:mode_frequency"] = fake.random_int(1000, 5000)
        stats["stat:category_frequencies"] = {cat: fake.random_int(100, 3000) for cat in categories}

    stats["stat:entropy"] = rand_float(1, 4)
    return stats

def mock_image_stats(params: Optional[Dict] = None) -> dict:
    params = params or {}
    min_w, max_w = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    min_h, max_h = sorted([fake.random_int(256, 1024), fake.random_int(1024, 4096)])
    modality = params.get("modality", random.choice(["X-ray", "MRI", "CT Scan"]))
    return {
        "@type": "ex:ImageStatistics", "ex:numImages": fake.random_int(500, 10000),
        "ex:imageDimensions": {"ex:minWidth": min_w, "ex:maxWidth": max_w, "ex:minHeight": min_h, "ex:maxHeight": max_h},
        "ex:colorMode": random.choice(["grayscale", "RGB"]), "ex:modality": modality,
    }

def mock_annotation_stats() -> dict:
    classes = sorted({*fake.words(nb=random.randint(2, 8), ext_word_list=["nodule", "fracture", "tumor", "lesion", "device"])})
    return {
        "@type": "ex:AnnotationStatistics", "ex:numAnnotations": fake.random_int(1000, 50000),
        "ex:numClasses": len(classes), "ex:classes": classes,
        "ex:objectsPerImage": {"ex:avg": rand_float(1, 5, 2), "ex:median": fake.random_int(1, 4)},
        "ex:boundingBoxStats": {"ex:avgRelativeWidth": rand_float(0.1, 0.5), "ex:avgRelativeHeight": rand_float(0.1, 0.5)},
    }

def mock_jsd_stats(domain_tokens: List[str]) -> dict:
    if not domain_tokens:
        domain_tokens = [fake.word() for _ in range(10)]
    num_tokens_to_sample = random.randint(5, min(10, len(domain_tokens)))
    tokens = random.sample(domain_tokens, num_tokens_to_sample)
    probs = _norm_dist([random.random() for _ in tokens])
    return {
        "@type": "jsd:TextDistribution",
        "jsd:total_records_analyzed": fake.random_int(500, 10000),
        "jsd:language": "en",
        "jsd:vocabulary_size": len(tokens),
        "jsd:top_k_tokens": [{"jsd:token": t, "jsd:frequency": p} for t, p in zip(tokens, probs)],
        "jsd:token_probability_vector": probs,
    }

def _strip_unwanted_keys(node: Any, allowed_prefixes: List[str]) -> Any:
    if isinstance(node, dict):
        for key in list(node.keys()):
            if ":" in key and not any(key.startswith(prefix) for prefix in allowed_prefixes):
                del node[key]
            else:
                node[key] = _strip_unwanted_keys(node[key], allowed_prefixes)
    elif isinstance(node, list):
        return [_strip_unwanted_keys(item, allowed_prefixes) for item in node]
    return node

def generate_mock_data(node: Any, domain: Dict) -> Any:
    """Recursively traverses the template and replaces values with mocked data."""
    domain_fields = domain["fields"]
    if isinstance(node, dict):
        if "@type" in node and node["@type"] == "cr:Field":
            field_id = node["@id"]
            if field_id in domain_fields:
                params = domain_fields[field_id].get("params")
                if "stat:statistics" in node:
                    stats_template = node["stat:statistics"]
                    if node["dataType"] in ["sc:Integer", "sc:Float"]:
                        node["stat:statistics"] = mock_numeric_stats(stats_template, params)
                    else:
                        node["stat:statistics"] = mock_categorical_stats(stats_template, params)
                if "jsd:textDistribution" in node:
                    domain_token_list = domain.get("jsd_tokens", [])
                    node["jsd:textDistribution"] = mock_jsd_stats(domain_token_list)

        if "ex:imageStats" in node:
            node["ex:imageStats"] = mock_image_stats({"modality": domain_fields.get("medical_images/modality")})
        if "ex:annotationStats" in node:
            node["ex:annotationStats"] = mock_annotation_stats()
        if "ex:datasetStats" in node:
            node["ex:datasetStats"] = mock_dataset_stats()

        return {k: generate_mock_data(v, domain) for k, v in node.items()}

    if isinstance(node, list):
        return [generate_mock_data(item, domain) for item in node]

    return node

def create_fingerprint(template: Dict, profile: Dict, domain: Dict) -> Dict:
    """Creates a single mocked fingerprint, tailored by a profile and a medical domain."""

    fp_template = deepcopy(template)
    croissant_body = fp_template["data"]["rawFingerprintJson"]

    domain_field_keys = set(domain["fields"].keys())
    filtered_record_sets = []
    for rs in croissant_body.get("recordSet", []):
        retained_fields = [field for field in rs.get("field", []) if field["@id"] in domain_field_keys]
        if retained_fields:
            rs["field"] = retained_fields
            filtered_record_sets.append(rs)
        elif rs["@id"] == "medical_images" and "medical_images/modality" in domain_field_keys:
             filtered_record_sets.append(rs)

    croissant_body["recordSet"] = filtered_record_sets

    domain_fields_with_new_ids = {}
    for rs in croissant_body["recordSet"]:
        for field in rs.get("field", []):
            original_id = field["@id"]
            domain_field_info = domain["fields"][original_id]
            new_name = random.choice(domain_field_info["variants"])
            field["name"] = new_name
            field["description"] = domain_field_info["description"]
            domain_fields_with_new_ids[original_id] = domain_field_info
    fp_mocked = generate_mock_data(fp_template, domain)
    croissant_body = fp_mocked["data"]["rawFingerprintJson"]
    profile_rs_ids = profile["record_set_ids"]
    all_domain_rs_ids = {rs["@id"] for rs in croissant_body["recordSet"]}

    if profile_rs_ids == "all":
        final_rs_ids = all_domain_rs_ids
    elif profile_rs_ids == "non_imaging":
        final_rs_ids = {id for id in all_domain_rs_ids if id != "medical_images"}
    else:
        final_rs_ids = set(profile_rs_ids)

    croissant_body["recordSet"] = [rs for rs in croissant_body["recordSet"] if rs["@id"] in final_rs_ids]
    if not profile.get("include_descriptions", True):
        croissant_body["description"] = "A minimally described dataset."
        for rs in croissant_body["recordSet"]:
            rs.pop("description", None)
            for field in rs.get("field", []):
                field.pop("description", None)

    allowed_prefixes = profile.get("extensions_to_keep", [])
    allowed_prefixes.extend(["sc:", "cr:", "name", "description", "@", "url", "license", "distribution", "recordSet", "field", "source"])
    _strip_unwanted_keys(croissant_body, allowed_prefixes)
    croissant_body["name"] = f"Mocked Dataset - {domain['name']} ({profile['name']})"
    croissant_body["description"] = domain['description']

    return fp_mocked


def get_access_token() -> Optional[str]:
    payload = {
        "client_id": API_CONFIG["KEYCLOAK_CLIENT_ID"],
        "grant_type": "password",
        "username": API_CONFIG["ADMIN_USERNAME"],
        "password": API_CONFIG["ADMIN_PASSWORD"],
    }
    try:
        print("🔑 Authenticating with Keycloak...")
        r = requests.post(API_CONFIG["KEYCLOAK_TOKEN_URL"], data=payload, timeout=10)
        r.raise_for_status()
        print("    ✓ Authentication successful.")
        return r.json().get("access_token")
    except requests.RequestException as e:
        print(f"    ✗ Auth error: {e}")
        return None

def create_organization_via_api(token: str, org_name: str) -> Optional[str]:
    url = f"{API_CONFIG['API_BASE_URL']}{API_CONFIG['CREATE_ORGANIZATION_ENDPOINT']}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "data": {
            "name": org_name,
            "visibility": "Public", 
            "visibleTo": []
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        response_data = r.json()
        org_id = response_data.get("data", {}).get("id")
        if org_id:
            print(f"    ✓ Organization '{org_name}' created successfully with ID: {org_id}")
            return org_id
        else:
            print(f"    ✗ Organization creation for '{org_name}' succeeded but no ID was returned.")
            return None
    except requests.RequestException as e:
        error_body = e.response.text if hasattr(e, "response") and e.response else "No response body."
        print(f"    ✗ Failed to create organization '{org_name}': {e}\n      Response Body: {error_body}")
        return None

def create_dataset_via_api(token: str, org_id: str, dataset_name: str, description: str) -> Optional[str]:
    url = f"{API_CONFIG['API_BASE_URL']}{API_CONFIG['CREATE_DATASET_ENDPOINT_TEMPLATE'].format(org_id=org_id)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "data": {
            "name": dataset_name,
            "description": description
        }
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        response_data = r.json()
        dataset_id = response_data.get("data", {}).get("id")
        if dataset_id:
            print(f"    ✓ Dataset '{dataset_name}' created successfully with ID: {dataset_id}")
            return dataset_id
        else:
            print(f"    ✗ Dataset creation for '{dataset_name}' succeeded but no ID was returned.")
            return None
    except requests.RequestException as e:
        error_body = e.response.text if hasattr(e, "response") and e.response else "No response body."
        print(f"    ✗ Failed to create dataset '{dataset_name}': {e}\n      Response Body: {error_body}")
        return None

def post_fingerprint_via_api(token: str, org_id: str, dataset_id: str, fingerprint: Dict) -> bool:
    url = f"{API_CONFIG['API_BASE_URL']}{API_CONFIG['CREATE_FINGERPRINT_ENDPOINT_TEMPLATE'].format(org_id=org_id, dataset_id=dataset_id)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    api_payload = {
        "data": {
            "type": fingerprint["data"]["type"],
            "version": fingerprint["data"]["version"],
            "candidateSearchVisibility": fingerprint["data"]["candidateSearchVisibility"],
            "isAnonymous": fingerprint["data"]["isAnonymous"],
            "rawFingerprintJson": fingerprint["data"]["rawFingerprintJson"]
        }
    }
    
    try:
        r = requests.post(url, headers=headers, json=api_payload, timeout=15)
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
    ap.add_argument("-c", "--count", type=int, default=500, help="Total number of mock fingerprints to generate.")
    ap.add_argument("--orgs", type=int, default=7, help="Number of organizations to create.")
    ap.add_argument("--datasets-per-org", type=int, default=2, help="Number of datasets to create per organization.")
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("-t", "--template-file", type=Path, default=DEFAULT_TPL)
    ap.add_argument("--send", action="store_true", help="Send generated fingerprints to the API after creating orgs and datasets.")
    args = ap.parse_args()

    master_template = read_template(args.template_file)
    weighted_profiles = [p for p in FINGERPRINT_PROFILES for _ in range(p["weight"])]
    if args.send:

        created_organizations = []
        
        token = get_access_token()
        if not token:
            print("\n✗ Unable to fetch auth token. Cannot proceed with API actions.")
            return

        print("\n--- STAGE 1: Creating Organizations and Datasets via API ---")
        org_dataset_map = []
        for i in range(1, args.orgs + 1):
            org_name = f"Mock-API-Org-{i}-{fake.company_suffix().lower()}"
            print(f"  • ({i}/{args.orgs}) Creating Organization: {org_name}")
            org_id = create_organization_via_api(token, org_name)
            if org_id:
                created_organizations.append({'name': org_name, 'id': org_id})

                for j in range(1, args.datasets_per_org + 1):
                    dataset_name = f"Dataset {j} for {org_name}"
                    dataset_desc = f"A mocked dataset containing {random.choice(MEDICAL_DOMAINS)['name']} data."
                    print(f"    • ({j}/{args.datasets_per_org}) Creating Dataset: {dataset_name}")
                    dataset_id = create_dataset_via_api(token, org_id, dataset_name, dataset_desc)
                    if dataset_id:
                        org_dataset_map.append({"org_id": org_id, "dataset_id": dataset_id, "org_name": org_name})
        
        if not org_dataset_map:
            print("\n✗ No organizations or datasets were created. Aborting fingerprint generation.")
            return

        print(f"\n--- STAGE 2: Generating and Posting {args.count} Fingerprints ---")
        for i in range(1, args.count + 1):
            target = random.choice(org_dataset_map)
            domain = random.choice(MEDICAL_DOMAINS)
            profile = random.choice(weighted_profiles)
            
            print(f"  • ({i}/{args.count}) Generating fingerprint for Org '{target['org_name']}'...")
            print(f"    (Domain: {domain['name']}, Profile: {profile['name']})")
            
            fp = create_fingerprint(master_template, profile, domain)
            post_fingerprint_via_api(token, target["org_id"], target["dataset_id"], fp)
            
            fname = f"api_mock_{domain['name']}_{profile['name']}_{i}.json"
            save_fingerprint(fp, fname, args.output_dir)

    else:
        print(f"Generating {args.count} mock fingerprint(s) locally from {args.template_file.name}")
        for i in range(1, args.count + 1):
            domain = random.choice(MEDICAL_DOMAINS)
            profile = random.choice(weighted_profiles)
            print(f"  • ({i}/{args.count}) profile: {profile['name']}, domain: {domain['name']}")
            
            fp = create_fingerprint(master_template, profile, domain)
            fp["data"]["datasetId"] = f"mock-dataset-id-{fake.uuid4()}"
            
            fname = f"local_mock_{domain['name']}_{profile['name']}_{i}.json"
            save_fingerprint(fp, fname, args.output_dir)
    if args.send and created_organizations:
        print("\n--- API Creation Summary ---")
        print(f"Successfully created {len(created_organizations)} organizations:")
        for org in created_organizations:
            print(f"  - Name: {org['name']}, ID: {org['id']}")
        print("--------------------------")
        
    print(f"\n✅ Successfully completed operations.")

if __name__ == "__main__":
    main()