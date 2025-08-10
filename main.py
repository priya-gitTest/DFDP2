# main.py
import json
import os
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from rdflib import Graph, URIRef
from io import BytesIO

# Define the file name for the RDF data
TURTLE_FILE_NAME = "dicom_mapped_with_catalog.ttl"

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
    query = """
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX custom_dicom: <http://example.org/dicom/private#>

    SELECT ?catalog ?catalogPublisher ?catalogIssued ?dataset ?datasetTitle ?datasetDescription ?datasetCreator ?datasetIssued ?datasetPublisher ?datasetIdentifier ?distribution ?conformsTo ?language ?name
    WHERE {
      ?catalog a dcat:Catalog .
      OPTIONAL { ?catalog dcterms:publisher ?catalogPublisher . }
      OPTIONAL { ?catalog dcterms:issued ?catalogIssued . }
      OPTIONAL { ?catalog dcterms:conformsTo ?conformsTo . }
      OPTIONAL { ?catalog dcterms:language ?language . }
      OPTIONAL { ?catalog custom_dicom:collectionName ?name . }
      OPTIONAL { ?catalog dcat:dataset ?dataset .
                 OPTIONAL { ?dataset dcterms:title ?datasetTitle . }
                 OPTIONAL { ?dataset dcterms:description ?datasetDescription . }
                 OPTIONAL { ?dataset dcterms:creator ?datasetCreator . }
                 OPTIONAL { ?dataset dcterms:issued ?datasetIssued . }
                 OPTIONAL { ?dataset dcterms:publisher ?datasetPublisher . }
                 OPTIONAL { ?dataset dcterms:identifier ?datasetIdentifier . }
                 OPTIONAL { ?dataset dcat:distribution ?distribution . }
               }
    }
    """
    
    qres = g.query(query)
    
    catalogs_data = defaultdict(lambda: {
        "metadata": {
            "conformsTo": "N/A", "publisher": "N/A", "language": "N/A", "issued": "N/A", "name": "N/A"
        },
        "datasets": defaultdict(lambda: {
            "title": "N/A", "description": "N/A", "numRecords": 0, "publisher": "N/A",
            "issued": "N/A", "identifier": "N/A", "creators": set()
        })
    })

    for row in qres:
        catalog_uri = str(row.catalog)
        
        # Process catalog metadata
        if row.conformsTo:
            catalogs_data[catalog_uri]["metadata"]["conformsTo"] = str(row.conformsTo)
        if row.catalogPublisher:
            catalogs_data[catalog_uri]["metadata"]["publisher"] = str(row.catalogPublisher)
        if row.language:
            catalogs_data[catalog_uri]["metadata"]["language"] = str(row.language)
        if row.catalogIssued:
            catalogs_data[catalog_uri]["metadata"]["issued"] = str(row.catalogIssued)
        if row.name:
            catalogs_data[catalog_uri]["metadata"]["name"] = str(row.name)

        # Process dataset data, only if a dataset is present in the row
        if row.dataset:
            dataset_uri = str(row.dataset)
            dataset = catalogs_data[catalog_uri]["datasets"][dataset_uri]
            
            dataset["title"] = str(row.datasetTitle) if row.datasetTitle else dataset["title"]
            dataset["description"] = str(row.datasetDescription) if row.datasetDescription else dataset["description"]
            if row.distribution:
                dataset["numRecords"] += 1
            if row.datasetPublisher:
                dataset["publisher"] = str(row.datasetPublisher)
            if row.datasetIssued:
                dataset["issued"] = str(row.datasetIssued)
            if row.datasetIdentifier:
                dataset["identifier"] = str(row.datasetIdentifier)
            if row.datasetCreator:
                dataset["creators"].add(str(row.datasetCreator))
    
    result_catalogs = []
    for catalog_uri, data in catalogs_data.items():
        datasets_list = []
        for dataset_uri, dataset_data in data["datasets"].items():
            datasets_list.append(
                CatalogItem(
                    uri=dataset_uri,
                    title=dataset_data["title"],
                    description=dataset_data["description"],
                    numRecords=dataset_data["numRecords"],
                    publisher=dataset_data["publisher"],
                    issued=dataset_data["issued"],
                    identifier=dataset_data["identifier"],
                    creators=sorted(list(dataset_data["creators"])),
                ).dict()
            )
        result_catalogs.append(
            Catalog(
                metadata=CatalogMetadata(**data["metadata"]),
                datasets=datasets_list
            ).dict()
        )
    
    return {"catalogs": result_catalogs}

@app.get("/api/visualize")
async def get_graph_data_for_visualization_api():
    """
    Extracts nodes and links from the graph for D3.js visualization.
    This is a simplified approach to demonstrate the concept.
    """
    nodes = {}
    links = []

    for s, p, o in g:
        # Add subject and object as nodes
        if s not in nodes:
            nodes[s] = {"id": str(s), "group": 1}
        if o not in nodes:
            nodes[o] = {"id": str(o), "group": 2}

        # Add the triple as a link
        links.append({"source": str(s), "target": str(o), "label": str(p)})

    return {"nodes": list(nodes.values()), "links": links}
