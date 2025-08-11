# main.py
import json
import os
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from rdflib import Graph, URIRef,BNode, Namespace
from io import BytesIO


# Define the file name for the RDF data
TURTLE_FILE_NAME = "dicom_mapped_with_catalog.ttl"
DCAT = Namespace("http://www.w3.org/ns/dcat#")

# Initialize an in-memory RDF graph
g = Graph()

# Attempt to load the Turtle file into the graph
try:
    if os.path.exists(TURTLE_FILE_NAME):
        g.parse(TURTLE_FILE_NAME, format="turtle")
        print(f"Successfully loaded {len(g)} triples from {TURTLE_FILE_NAME}")
    else:
        print(f"Warning: {TURTLE_FILE_NAME} not found. The graph is empty.")
except Exception as e:
    print(f"Error loading RDF file: {e}")

# Initialize FastAPI application
app = FastAPI(title="DICOM RDF Knowledge Graph API")

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SPARQLQuery(BaseModel):
    query: str

class CatalogMetadata(BaseModel):
    conformsTo: str | None
    publisher: str | None
    language: str | None
    issued: str | None
    name: str | None

class CatalogItem(BaseModel):
    uri: str
    title: str | None
    description: str | None
    numRecords: int
    publisher: str | None
    issued: str | None
    identifier: str | None
    creators: list[str]

class Catalog(BaseModel):
    metadata: CatalogMetadata
    datasets: list[CatalogItem]

@app.get("/rdf/{catalog_name}", response_class=Response)
async def download_catalog_rdf_file(catalog_name: str):
    """
    Constructs a subgraph for a specific catalog and returns it as a downloadable Turtle file.
    """
    result_graph = Graph()
    
    # **MODIFICATION**: Correctly iterate over the namespaces
    for prefix, namespace in g.namespaces():
        result_graph.bind(prefix, namespace)

    catalog_uri = URIRef(f"http://example.org/catalog/{catalog_name}")

    if (catalog_uri, None, None) not in g:
        raise HTTPException(status_code=404, detail=f"Catalog '{catalog_name}' not found.")

    for s, p, o in g.triples((catalog_uri, None, None)):
        result_graph.add((s, p, o))
        
        if p == DCAT.dataset:
            dataset_uri = o
            for s_ds, p_ds, o_ds in g.triples((dataset_uri, None, None)):
                result_graph.add((s_ds, p_ds, o_ds))

                if p_ds == DCAT.distribution:
                    dist_uri = o_ds
                    if not isinstance(dist_uri, BNode):
                        for s_dist, p_dist, o_dist in g.triples((dist_uri, None, None)):
                            result_graph.add((s_dist, p_dist, o_dist))

    ttl_data = result_graph.serialize(format="turtle")
    
    headers = {
        'Content-Disposition': f'attachment; filename="{catalog_name}.ttl"'
    }
    
    return Response(content=ttl_data, media_type="text/turtle", headers=headers)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/catalog", response_class=HTMLResponse)
async def get_catalog_page(request: Request):
    return templates.TemplateResponse("catalog.html", {"request": request})

@app.get("/visualize", response_class=HTMLResponse)
async def get_visualize_page(request: Request):
    return templates.TemplateResponse("visualize.html", {"request": request})

@app.get("/sparql", response_class=HTMLResponse)
async def get_sparql_page(request: Request):
    """
    Serves the HTML template for the SPARQL query interface.
    """
    return templates.TemplateResponse("sparql.html", {"request": request})

@app.post("/sparql")
async def sparql_query_endpoint(sparql_query: SPARQLQuery):
    """
    Executes a SPARQL query against the in-memory graph.
    """
    try:
        qres = g.query(sparql_query.query)
        results = [row.asdict() for row in qres]
        
        # Convert URIRef objects to strings for JSON serialization
        for result in results:
            for key, value in result.items():
                if isinstance(value, URIRef):
                    result[key] = str(value)
                elif isinstance(value, int):
                    result[key] = int(value)

        return JSONResponse(content={"results": results})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing SPARQL query: {e}")

@app.get("/api/catalog")
async def get_catalog_datasets_api():
    """
    Retrieves a list of all catalogs, each containing its metadata and datasets.
    """
    # **MODIFICATION**: Added ?datasetIssued to the SELECT and WHERE clauses.
    query = """
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT 
      ?catalog 
      ?catalogTitle
      ?catalogPublisher
      ?catalogIssued
      ?catalogLanguage
      ?dataset 
      ?datasetTitle 
      ?datasetDescription
      ?datasetIdentifier
      ?datasetIssued
      (COUNT(?distribution) AS ?numRecords)
    WHERE {
      ?catalog a dcat:Catalog .
      ?catalog dcat:dataset ?dataset .
      ?dataset dcat:distribution ?distribution .

      OPTIONAL { ?catalog dcterms:title ?catalogTitle . }
      OPTIONAL { ?catalog dcterms:publisher ?catalogPublisher . }
      OPTIONAL { ?catalog dcterms:issued ?catalogIssued . }
      OPTIONAL { ?catalog dcterms:language ?catalogLanguage . }
      OPTIONAL { ?dataset dcterms:title ?datasetTitle . }
      OPTIONAL { ?dataset dcterms:description ?datasetDescription . }
      OPTIONAL { ?dataset dcterms:identifier ?datasetIdentifier . }
      OPTIONAL { ?dataset dcterms:issued ?datasetIssued . }
    }
    GROUP BY ?catalog ?catalogTitle ?catalogPublisher ?catalogIssued ?catalogLanguage ?dataset ?datasetTitle ?datasetDescription ?datasetIdentifier ?datasetIssued
    ORDER BY ?catalogTitle ?datasetTitle
    """
    
    try:
        qres = g.query(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPARQL query failed: {e}")

    catalogs_data = defaultdict(lambda: {
        "metadata": None,
        "datasets": []
    })

    for row in qres:
        catalog_uri = str(row.catalog)
        
        if catalogs_data[catalog_uri]["metadata"] is None:
             catalogs_data[catalog_uri]["metadata"] = CatalogMetadata(
                publisher=str(row.catalogPublisher) if row.catalogPublisher else None,
                name=str(row.catalogTitle) if row.catalogTitle else "Untitled Catalog",
                language=str(row.catalogLanguage) if row.catalogLanguage else None,
                issued=str(row.catalogIssued) if row.catalogIssued else None,
                conformsTo=None
             )

        # Append dataset info for the current catalog
        catalogs_data[catalog_uri]["datasets"].append(
            CatalogItem(
                uri=str(row.dataset),
                title=str(row.datasetTitle) if row.datasetTitle else "Untitled Dataset",
                description=str(row.datasetDescription) if row.datasetDescription else "",
                numRecords=int(row.numRecords),
                identifier=str(row.datasetIdentifier) if row.datasetIdentifier else "N/A",
                publisher=str(row.catalogPublisher) if row.catalogPublisher else "N/A",
                # **MODIFICATION**: Pass the newly queried ?datasetIssued value.
                issued=str(row.datasetIssued) if row.datasetIssued else None,
                creators=[]
            ).dict()
        )
    
    # Format the final output
    final_catalogs = []
    for uri, data in catalogs_data.items():
        meta_dict = data["metadata"].dict()
        meta_dict["uri"] = uri
        
        final_catalogs.append({
            "metadata": meta_dict,
            "datasets": data["datasets"]
        })
        
    return {"catalogs": final_catalogs}

# In main.py, replace the /api/visualize endpoint function

# In main.py, find and replace the entire @app.get("/api/visualize") function

@app.get("/api/visualize")
async def get_graph_data_for_visualization_api():
    """
    Extracts a structured graph of catalogs, datasets, patients, studies, 
    and series for visualization.
    """
    query = """
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>
    PREFIX roo: <http://www.cancerdata.org/roo/>

    SELECT DISTINCT
      ?catalogURI ?catalogTitle
      ?datasetURI ?datasetTitle
      ?patientID ?gender ?age ?patientHistory
      ?studyUID ?modality ?bodyPartExamined ?anatomicSite
      ?seriesUID ?seriesDescription
    WHERE {
      ?catalogURI a dcat:Catalog ;
                  dcterms:title ?catalogTitle ;
                  dcat:dataset ?datasetURI .
      ?datasetURI a dcat:Dataset ;
                  dcterms:title ?datasetTitle ;
                  dcat:distribution ?distribution .
      ?distribution dicom:PatientID ?patientID ;
                    dicom:StudyInstanceUID ?studyUID ;
                    dicom:SeriesInstanceUID ?seriesUID .
      
      OPTIONAL { ?distribution roo:hasSex ?gender . }
      OPTIONAL { ?distribution roo:hasAge ?age . }
      OPTIONAL { ?distribution roo:hasPatientHistory ?patientHistory . }
      OPTIONAL { ?distribution dicom:Modality ?modality . }
      OPTIONAL { ?distribution dicom:BodyPartExamined ?bodyPartExamined . }
      OPTIONAL { ?distribution roo:hasAnatomicSite ?anatomicSite . }
      OPTIONAL { ?distribution dicom:SeriesDescription ?seriesDescription . }
    }
    ORDER BY ?catalogTitle ?datasetTitle ?patientID ?studyUID
    """
    
    try:
        # Convert results to a list to allow multiple iterations
        results = list(g.query(query))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing SPARQL query: {e}")

    nodes = {}
    links = []
    
    # Use a dictionary to store all data, keyed by a tuple of identifiers
    # This ensures that each unique entity is processed only once
    graph_data = {}

    for row in results:
        # Create a unique key for each row to avoid duplicates
        key = (
            str(row.catalogURI),
            str(row.datasetURI),
            str(row.patientID),
            str(row.studyUID),
            str(row.seriesUID)
        )
        
        # If we haven't processed this combination, store its details
        if key not in graph_data:
            graph_data[key] = {
                "catalogTitle": str(row.catalogTitle),
                "datasetTitle": str(row.datasetTitle),
                "gender": str(row.gender) if row.gender else "N/A",
                "age": str(row.age) if row.age else "N/A",
                "patientHistory": str(row.patientHistory) if row.patientHistory else "N/A",
                "modality": str(row.modality) if row.modality else "N/A",
                "bodyPartExamined": str(row.bodyPartExamined) if row.bodyPartExamined else "N/A",
                "anatomicSite": str(row.anatomicSite) if row.anatomicSite else "N/A",
                "seriesDescription": str(row.seriesDescription) if row.seriesDescription else "N/A"
            }

    # Now, build the nodes and links from the aggregated data
    for key, details in graph_data.items():
        catalog_uri, dataset_uri, patient_id, study_uid, series_uid = key

        # Define unique node IDs
        catalog_node_id = catalog_uri
        dataset_node_id = dataset_uri
        patient_node_id = f"patient_{patient_id}"
        study_node_id = study_uid
        series_node_id = series_uid

        # Add nodes if they don't already exist
        if catalog_node_id not in nodes:
            nodes[catalog_node_id] = {"id": catalog_node_id, "label": details["catalogTitle"], "group": 1, "title": f"Catalog: {details['catalogTitle']}"}
        
        if dataset_node_id not in nodes:
            nodes[dataset_node_id] = {"id": dataset_node_id, "label": details["datasetTitle"], "group": 2, "title": f"Dataset: {details['datasetTitle']}"}
        
        # Patient node
        if patient_node_id not in nodes:
            patient_label = (
                f"Patient: {patient_id}\n"
                f"Gender: {details['gender']}\n"
                f"Age: {details['age']}\n"
                f"History: {details['patientHistory']}"
            )
            nodes[patient_node_id] = {
                "id": patient_node_id,
                "label": patient_label,
                "group": 3
            }

        # Study node
        if study_node_id not in nodes:
            study_label = (
                f"Study UID: {study_uid}\n"
                f"Modality: {details['modality']}\n"
                f"Body Part: {details['bodyPartExamined']}\n"
                f"Anatomic Site: {details['anatomicSite']}"
            )
            nodes[study_node_id] = {
                "id": study_node_id,
                "label": study_label,
                "group": 4
            }

        # Series node
        if series_node_id not in nodes:
            series_label = (
                f"Series UID: {series_uid}\n"
                f"Description: {details['seriesDescription']}"
            )
            nodes[series_node_id] = {
                "id": series_node_id,
                "label": series_label,
                "group": 5
            }

        # Add links between the nodes
        links.extend([
            {"source": catalog_node_id, "target": dataset_node_id},
            {"source": dataset_node_id, "target": patient_node_id},
            {"source": patient_node_id, "target": study_node_id},
            {"source": study_node_id, "target": series_node_id}
        ])

    # Remove duplicate links
    unique_links = [dict(t) for t in {tuple(d.items()) for d in links}]

    return {"nodes": list(nodes.values()), "links": unique_links}
