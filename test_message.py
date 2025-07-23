# File: ppfl-python-worker/publish_test_message.py
import asyncio
import json
import uuid
from aio_pika import connect_robust, Message
from loguru import logger

from app.core.config import settings
from app.models.messages import * 
from app.services.fingerprint import get_fingerprints_by_ids
from app.core.mongodb import db as mongodb_db 

# Define the RabbitMQ URL for local script execution
RABBITMQ_URL_FOR_SCRIPT = "amqp://guest:guest@localhost:5672/"

logger.remove()
logger.add(lambda msg: print(msg, end=""), level="DEBUG", colorize=True)

async def main():

    TEST_ROOT_FINGERPRINT_IDS = [
        "e72a6e61-75af-4bcf-a663-88cda436b8ad",
        "9c6f29c0-df65-427e-928f-25c78ed6d7a7" 
    ]
    ACTUAL_EXPERIMENT_ID = "1f776111-9ce2-414b-99e3-1853e7ca371e"
    ACTUAL_ORGANIZATION_ID = "fb7f55b2-9c08-4d35-b2db-4be3994f7b69"
    MOCK_JOB_ID = str(uuid.uuid4())
    
    logger.info(f"Using Root Fingerprint IDs: {TEST_ROOT_FINGERPRINT_IDS}")
    logger.info(f"Using Actual Experiment ID: {ACTUAL_EXPERIMENT_ID}")
    logger.info(f"Using Actual Organization ID: {ACTUAL_ORGANIZATION_ID}")
    logger.info(f"Generated Mock Job ID: {MOCK_JOB_ID}")

    HARDCODED_CANDIDATE_IDS = [
        "08c2ae43-8d21-4d6b-b4ed-c9b6ad6254db", "739c4d7b-8a26-49b1-a4ca-70f1da1ec4c4",
        "0fc320d6-3e6c-49f5-806f-d4db89fd5962", "d19587cc-e2dd-4619-9168-2364a45bb235",
        "cca05feb-d1a4-4006-b9c7-42e1e2eeda6f", "fc62c2f7-7963-4e45-9b96-0ed8762cb037",
        "50264395-719d-45d9-9bd1-78c0e5332ae1", "aa4a3e91-489b-4ec4-aa02-653cd29b7f0e",
        "e017ccc3-24ad-4199-8cc5-58833d012a7a", "d3770dc8-3275-4a4b-ba17-741079d44f2b",
        "ac3d88de-9892-4b55-904e-d7460ee8dd68", "819db5c6-3718-456d-a2e2-47a35cf106f0",
        "666d696d-8228-49fc-8c6f-6499d69e361b", "2799ff84-0aab-4081-96cd-b8d0631f3a9d",
        "b308145b-0102-403e-ab04-0a71aeff37dc", "9d5648da-5a97-400b-a3e9-b04c7ee6a16c",
        "6c9a5a41-c0d0-48da-8e67-950ae7e5854e", "22a34431-4f68-4b09-835a-d0d9c0be18bb",
        "a920bda1-7dc7-4b50-b97a-6d6cd109c278", "3d9fc6ee-4fbb-45b1-b341-bc1c35548bcf"
    ]
    
    logger.info(f"Using a hardcoded list of {len(HARDCODED_CANDIDATE_IDS)} candidates to avoid rate limits.")

    await mongodb_db.connect()

    all_fingerprint_ids = TEST_ROOT_FINGERPRINT_IDS + HARDCODED_CANDIDATE_IDS
    fingerprint_docs_map = await get_fingerprints_by_ids(all_fingerprint_ids)
    
    root_fingerprints = []
    for fp_id in TEST_ROOT_FINGERPRINT_IDS:
        dataset_id = "mock-ds"
        if fp_id in fingerprint_docs_map:
            dataset_id = fingerprint_docs_map[fp_id].datasetId
            logger.info(f"Retrieved actual dataset ID for root '{fp_id}': {dataset_id}")
        else:
            logger.warning(f"Root fingerprint {fp_id} not found in DB. Using mock dataset ID.")
        root_fingerprints.append(FingerprintInfoDto(fingerprintId=fp_id, organizationId=ACTUAL_ORGANIZATION_ID, datasetId=dataset_id))

    candidate_fingerprints = []
    for fp_id in HARDCODED_CANDIDATE_IDS:
        dataset_id = "mock-ds"
        if fp_id in fingerprint_docs_map:
            dataset_id = fingerprint_docs_map[fp_id].datasetId
        else:
            logger.warning(f"Candidate fingerprint {fp_id} not found in DB. Using mock dataset ID.")
        candidate_fingerprints.append(FingerprintInfoDto(fingerprintId=fp_id, organizationId=ACTUAL_ORGANIZATION_ID, datasetId=dataset_id))
    spec = CandidateSearchSpecification(
        algorithmType=0,
        objective=Objective(problemType="Federated Learning Candidate Discovery", description="Find datasets with similar patient age distributions."),
        datasetRequirements=DatasetRequirements(minSamples=50, featureTypes=["sc:Integer", "sc:Text", "sc:Boolean", "sc:Float"], balancedClassDistribution=False),
        featuresMapping=[
            FieldMapping(root_field_id="patient_demographics/patient_age", candidate_field_id="patient_demographics/patient_age", comparison_type="statistical"),
            FieldMapping(root_field_id="vital_signs/bmi", candidate_field_id="vital_signs/bmi", comparison_type="statistical"),
            FieldMapping(root_field_id="patient_demographics/patient_blood_type", candidate_field_id="patient_demographics/patient_blood_type", comparison_type="statistical"),
            FieldMapping(root_field_id="clinical_notes/notes", candidate_field_id="clinical_notes/notes", comparison_type="semantic")
        ],
        modelSpecification=ModelSpecification(modelType="N/A", compatibleDataTypes=["*"], modelArchitecture=ModelArchitecture(n_estimators=0, max_depth=0)),
        federatedConstraints=FederatedConstraints(privacy=Privacy(differentialPrivacy=False, epsilon=0), aggregationMethod="N/A", communicationRounds=0),
        matchingPreferences=MatchingPreferences(semanticWeight=0.5, statisticalWeight=0.5, driftTolerance="Medium"),
        similarityThreshold=0.6,
        maxCandidates=25,
        dataQuality=DataQuality(missingPercentage=30, outlierDetectionMethod="IQR", classImbalanceRatio="N/A", qualityScore=0.7),
        preProcessing=PreProcessing(normalizationTechnique="None", missingValueHandling="None", encoding="None", typeCasting="None", statisticalTransformations=[], featureEngineeringSteps=[]),
        labels=Labels(labelingTechnique="None", labelDescription="", requiredLabels=[], manualRelabelingRequired=False, partialLabelAcceptance=False)
    )

    pbi_request = CandidateSearchRequest(
        experimentId=ACTUAL_EXPERIMENT_ID,
        candidateSearchJobId=MOCK_JOB_ID,
        rootFingerprints=root_fingerprints,
        candidateFingerprints=candidate_fingerprints,
        specification=spec
    )
    
    logger.debug(f"Generated CandidateSearchRequest: {pbi_request.model_dump_json(indent=2)}")

    try:
        connection = await connect_robust(RABBITMQ_URL_FOR_SCRIPT)
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(settings.input_queue, durable=True)
            message_body = pbi_request.model_dump_json(by_alias=True).encode('utf-8')
            message = Message(message_body, delivery_mode=2)
            await channel.default_exchange.publish(message, routing_key=settings.input_queue)
            logger.success(f"Published message for job '{pbi_request.candidateSearchJobId}' to queue '{settings.input_queue}'.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        await mongodb_db.close() 

if __name__ == "__main__":
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="DEBUG", colorize=True)
    asyncio.run(main())