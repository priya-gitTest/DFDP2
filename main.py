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
