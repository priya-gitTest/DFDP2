
# main.py
# A self-contained FastAPI application for DICOM metadata processing, RDF generation,
# and knowledge graph visualization.
# To run:
# 1. Install necessary libraries: pip install fastapi uvicorn "pydantic[email]" pydicom rdflib requests python-multipart jinja2
# 2. Save this file as main.py
# 3. Run the server: uvicorn main:app --reload

import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid

from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, DCTERMS, XSD, FOAF
from rdflib.plugins.sparql import prepareQuery

# --- Configuration & Namespaces ---
# Using namespaces for creating well-formed RDF data.
BASE_URI = "http://local.dev/dicom-demo/"
DATASET_URI = URIRef(f"{BASE_URI}dataset/")
PID_PREFIX = "https://w3id.org/purl/pid/"

# Standard and custom namespaces
ROO = Namespace("http://www.cancerdata.org/roo/")
SNOMED = Namespace("http://snomed.info/sct/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
HDCAT = Namespace("http://health.data.gov.eu/def/dcat-ap/")
SCHEMA = Namespace("http://schema.org/")

# In-memory graph to store RDF triples
rdf_graph = Graph()

# FastAPI application setup
app = FastAPI(
    title="DICOM RDF Processor",
    description="A demo for processing DICOM metadata, generating RDF, and providing a SPARQL endpoint.",
    version="1.0.0"
)

# Setup for templates and static files
templates = Jinja2Templates(directory="templates")
# This is a bit of a trick for a single-file app. We'll create the dir if it doesn't exist.
if not os.path.exists("templates"):
    os.makedirs("templates")
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Mock Data Generation ---
# In a real scenario, you would process actual DICOM files.
# For this demo, we generate mock DICOM data.

def create_mock_dicom_file(file_path: str, patient_id: str, study_date: str, modality: str, accession_number: str):
    """Generates a mock DICOM file with essential metadata."""
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.ImplicitVRLittleEndian
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = file_meta

    ds.PatientID = patient_id
    ds.StudyDate = study_date
    ds.Modality = modality
    ds.AccessionNumber = accession_number
    ds.PatientName = f"Anonymized^{patient_id}"
    ds.StudyDescription = f"Study for {modality}"
    ds.SOPClassUID = pydicom.uid.RTImageStorage
    ds.is_little_endian = True
    ds.is_implicit_VR = True

    ds.save_as(file_path, write_like_original=False)

def generate_initial_dicom_files():
    """Generates 50 mock DICOM files for initial processing."""
    dicom_dir = "dicom_files"
    if not os.path.exists(dicom_dir):
        os.makedirs(dicom_dir)
    
    modalities = ["CT", "MR", "RTSTRUCT", "RTPLAN", "RTDOSE"]
    for i in range(50):
        patient_id = f"PAT_{1000 + i}"
        study_date = datetime(2023, (i % 12) + 1, (i % 28) + 1).strftime('%Y%m%d')
        modality = modalities[i % len(modalities)]
        accession_number = f"ACC_{5000 + i}"
        file_path = os.path.join(dicom_dir, f"file_{i}.dcm")
        create_mock_dicom_file(file_path, patient_id, study_date, modality, accession_number)
    return dicom_dir

# --- Metadata Extraction and Mapping ---
def extract_dicom_metadata(file_path: str) -> Dict[str, Any]:
    """Extracts relevant metadata from a DICOM file."""
    try:
        ds = pydicom.dcmread(file_path, force=True)
        return {
            "PatientID": getattr(ds, "PatientID", "N/A"),
            "StudyDate": getattr(ds, "StudyDate", "N/A"),
            "Modality": getattr(ds, "Modality", "N/A"),
            "AccessionNumber": getattr(ds, "AccessionNumber", "N/A"),
            "FilePath": file_path
        }
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def map_to_ontologies(metadata: Dict[str, Any]) -> Dict[str, URIRef]:
    """Maps extracted metadata to ROO and SNOMED CT concepts."""
    # This is a simplified mapping. A real implementation would use a more robust lookup service.
    modality_map = {
        "CT": SNOMED["7771000"],  # Computed tomography
        "MR": SNOMED["25064002"], # Magnetic resonance imaging
        "RTSTRUCT": ROO["ROO_00473"], # Radiotherapy Structure Set
        "RTPLAN": ROO["ROO_00469"],   # Radiotherapy Plan
        "RTDOSE": ROO["ROO_00472"],   # Radiotherapy Dose
    }
    
    mapped_data = {}
    modality = metadata.get("Modality")
    if modality and modality in modality_map:
        mapped_data["ModalityConcept"] = modality_map[modality]
    
    # Map PatientID to a persistent identifier
    patient_pid = URIRef(f"{PID_PREFIX}patient/{metadata['PatientID']}")
    mapped_data["PatientPID"] = patient_pid

    return mapped_data

# --- RDF Generation ---
def generate_rdf_triples(metadata: Dict[str, Any], mapped_data: Dict[str, Any]):
    """Generates RDF triples for a single DICOM file and adds them to the graph."""
    # Create a unique URI for the DICOM dataset instance
    instance_id = os.path.basename(metadata['FilePath'])
    instance_uri = URIRef(f"{DATASET_URI}{instance_id}")

    # Add triples
    rdf_graph.add((instance_uri, RDF.type, HDCAT.Dataset))
    rdf_graph.add((instance_uri, DCTERMS.identifier, Literal(instance_id)))
    rdf_graph.add((instance_uri, DCTERMS.title, Literal(f"DICOM data for {metadata['PatientID']} on {metadata['StudyDate']}")))
    
    # Link to patient PID
    patient_pid = mapped_data.get("PatientPID")
    if patient_pid:
        rdf_graph.add((instance_uri, DCTERMS.subject, patient_pid))
        rdf_graph.add((patient_pid, RDF.type, FOAF.Person))
        rdf_graph.add((patient_pid, SCHEMA.identifier, Literal(metadata['PatientID'])))

    # Add modality information
    modality_concept = mapped_data.get("ModalityConcept")
    if modality_concept:
        rdf_graph.add((instance_uri, DCAT.theme, modality_concept))
        # Add labels for better visualization/querying
        rdf_graph.add((modality_concept, RDFS.label, Literal(metadata['Modality'])))

    # Add other metadata
    rdf_graph.add((instance_uri, SCHEMA.accessionNumber, Literal(metadata['AccessionNumber'])))
    #rdf_graph.add((instance_uri, DCTERMS.issued, Literal(metadata['StudyDate'], datatype=XSD.date)))
    from datetime import datetime

    # Convert 'YYYYMMDD' to 'YYYY-MM-DD'
    raw_date = metadata['StudyDate']
    try:
        formatted_date = datetime.strptime(raw_date, '%Y%m%d').date().isoformat()
        rdf_graph.add((instance_uri, DCTERMS.issued, Literal(formatted_date, datatype=XSD.date)))
    except ValueError:
        print(f"Invalid StudyDate format: {raw_date}")

def process_all_dicoms(dicom_dir: str):
    """Processes all DICOM files in a directory."""
    for filename in os.listdir(dicom_dir):
        if filename.endswith(".dcm"):
            file_path = os.path.join(dicom_dir, filename)
            metadata = extract_dicom_metadata(file_path)
            if metadata:
                mapped_data = map_to_ontologies(metadata)
                generate_rdf_triples(metadata, mapped_data)
    print(f"Processed {len(rdf_graph)} triples from DICOM files.")


# --- Application Startup ---
@app.on_event("startup")
def on_startup():
    """Initializes the application state on startup."""
    # 1. Generate mock data
    dicom_dir = generate_initial_dicom_files()
    # 2. Process data and populate RDF graph
    process_all_dicoms(dicom_dir)
    # 3. Create HTML templates in memory (since we can't ship files easily)
   # create_html_templates()

# --- FastAPI Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_main_page(request: Request):
    """Serves the main web interface."""
    return templates.TemplateResponse("index.html", {"request": request, "title": "DICOM RDF Demo"})

@app.get("/catalog", response_class=HTMLResponse)
async def get_catalog(
    request: Request,
    modality: str = None,
    accession: str = None
):
    """
    Serves the Health DCAT-AP compliant metadata catalog.
    Enables dataset discovery via Modality and Accession Number.
    """
    query_str = """
        SELECT ?dataset ?title ?patientId ?studyDate ?modalityLabel ?accessionNumber
        WHERE {
            ?dataset a <http://health.data.gov.eu/def/dcat-ap/Dataset> .
            ?dataset <http://purl.org/dc/terms/title> ?title .
            ?dataset <http://purl.org/dc/terms/subject> ?patient .
            ?patient <http://schema.org/identifier> ?patientId .
            ?dataset <http://purl.org/dc/terms/issued> ?studyDate .
            ?dataset <http://www.w3.org/ns/dcat#theme> ?modality .
            ?modality <http://www.w3.org/2000/01/rdf-schema#label> ?modalityLabel .
            ?dataset <http://schema.org/accessionNumber> ?accessionNumber .
    """
    # Add filters for discovery
    filters = []
    if modality:
        filters.append(f'FILTER(CONTAINS(LCASE(?modalityLabel), LCASE("{modality}")))')
    if accession:
        filters.append(f'FILTER(CONTAINS(?accessionNumber, "{accession}")))')
    
    if filters:
        query_str += " ".join(filters)
        
    query_str += "} ORDER BY ?studyDate"

    results = rdf_graph.query(query_str)
    
    datasets = [
        {
            "id": str(row.dataset).split('/')[-1],
            "title": str(row.title),
            "patientId": str(row.patientId),
            "studyDate": str(row.studyDate),
            "modality": str(row.modalityLabel),
            "accessionNumber": str(row.accessionNumber)
        } for row in results
    ]
    
    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "datasets": datasets,
        "filter_modality": modality or "",
        "filter_accession": accession or ""
    })

@app.get("/visualize", response_class=HTMLResponse)
async def get_visualization_page(request: Request):
    """Serves the knowledge graph visualization page."""
    return templates.TemplateResponse("visualize.html", {"request": request})

@app.get("/graph-data")
async def get_graph_data():
    """Provides the RDF graph data in a D3-compatible JSON format."""
    nodes = {}
    links = []

    for s, p, o in rdf_graph:
        # Add nodes
        for item in [s, o]:
            if isinstance(item, URIRef):
                if str(item) not in nodes:
                    label = str(item).split('/')[-1].replace("_", " ")
                    group = 1 # Default
                    if 'patient' in str(item): group = 2
                    elif 'snomed' in str(item) or 'roo' in str(item): group = 3
                    nodes[str(item)] = {"id": str(item), "label": label, "group": group}
        
        # Add links
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            links.append({
                "source": str(s),
                "target": str(o),
                "predicate": str(p).split('/')[-1].split('#')[-1]
            })

    return JSONResponse(content={"nodes": list(nodes.values()), "links": links})

@app.post("/sparql")
async def sparql_endpoint(request: Request, query: str = Form(...)):
    """A SPARQL 1.1 compliant endpoint to query the RDF data."""
    try:
        # The form gives us a string, rdflib's query function handles it
        results = rdf_graph.query(query)
        
        # Serialize results to JSON
        results_json = results.serialize(format='json')
        return JSONResponse(content=json.loads(results_json))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SPARQL query failed: {e}")

@app.post("/upload-dicom/", response_class=HTMLResponse)
async def upload_dicom_file(request: Request, file: UploadFile = File(...)):
    """Allows uploading a new DICOM file for processing."""
    upload_dir = "dicom_uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # Process the new file
    metadata = extract_dicom_metadata(file_path)
    if metadata:
        mapped_data = map_to_ontologies(metadata)
        generate_rdf_triples(metadata, mapped_data)
        message = f"Successfully processed and added '{file.filename}' to the graph. Triples: {len(rdf_graph)}"
    else:
        message = f"Failed to process '{file.filename}'."
        
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "DICOM RDF Demo",
        "upload_message": message
    })
if __name__ == "__main__":
    import uvicorn
    # This part is for running directly with `python main.py`
    # Note: Uvicorn's auto-reload works best when called from the command line.
    print("Starting server. Run with 'uvicorn main:app --reload' for auto-reloading.")
    uvicorn.run(app, host="127.0.0.1", port=8000)

