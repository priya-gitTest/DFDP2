# main.py
import json
import os
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

class CatalogItem(BaseModel):
    uri: str
    title: str
    description: str

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

        return JSONResponse(content={"results": results})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing SPARQL query: {e}")

@app.get("/api/catalog")
async def get_catalog_datasets_api():
    """
    Retrieves a list of datasets from the catalog.
    """
    query = """
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    SELECT ?dataset ?title ?description
    WHERE {
      ?catalog a dcat:Catalog ;
               dcat:dataset ?dataset .
      ?dataset dcterms:title ?title ;
               dcterms:description ?description .
    }
    """
    try:
        qres = g.query(query)
        catalog_items = []
        for row in qres:
            catalog_items.append(
                CatalogItem(
                    uri=str(row.dataset),
                    title=str(row.title),
                    description=str(row.description)
                ).dict()
            )
        return {"datasets": catalog_items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying catalog: {e}")

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
