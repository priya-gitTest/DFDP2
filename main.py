from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDF, DCAT
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATA_FILE = "dicom_mapped_with_catalog.ttl"

# Load RDF graph once at startup
rdf_graph = Graph()
if os.path.exists(DATA_FILE):
    rdf_graph.parse(DATA_FILE, format="turtle")
else:
    print(f"Warning: RDF data file {DATA_FILE} not found.")

# Namespaces you might use (extend as needed)
DCT = Namespace("http://purl.org/dc/terms/")
DCAT_NS = Namespace("http://www.w3.org/ns/dcat#")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "DICOM to RDF Demo", "upload_message": None})

@app.post("/sparql")
async def sparql_query(query: str = Form(...)):
    try:
        qres = rdf_graph.query(query)
        results = []
        for row in qres:
            row_dict = {}
            for idx, var in enumerate(qres.vars):
                val = row[idx]
                row_dict[str(var)] = str(val) if val is not None else None
            results.append(row_dict)
        return JSONResponse(content={"results": results})
    except Exception as e:
        return JSONResponse(content={"detail": str(e)}, status_code=400)

@app.get("/catalog", response_class=HTMLResponse)
async def catalog(request: Request, modality: str = None, accession: str = None):
    datasets = []
    for s in rdf_graph.subjects(RDF.type, DCAT_NS.Dataset):
        dataset = {"id": str(s), "title": None, "patientId": None, "studyDate": None, "modality": None, "accessionNumber": None}
        title = rdf_graph.value(s, DCT.title)
        if title:
            dataset["title"] = str(title)
        patientId = rdf_graph.value(s, URIRef("http://example.org/patientId"))
        if patientId:
            dataset["patientId"] = str(patientId)
        studyDate = rdf_graph.value(s, URIRef("http://example.org/studyDate"))
        if studyDate:
            dataset["studyDate"] = str(studyDate)
        modalityVal = rdf_graph.value(s, URIRef("http://example.org/modality"))
        if modalityVal:
            dataset["modality"] = str(modalityVal)
        accessionNum = rdf_graph.value(s, URIRef("http://example.org/accessionNumber"))
        if accessionNum:
            dataset["accessionNumber"] = str(accessionNum)

        if modality and modality.lower() not in (dataset["modality"] or "").lower():
            continue
        if accession and accession.lower() not in (dataset["accessionNumber"] or "").lower():
            continue

        datasets.append(dataset)

    return templates.TemplateResponse("catalog.html", {
        "request": request,
        "datasets": datasets,
        "filter_modality": modality or "",
        "filter_accession": accession or "",
        "title": "Metadata Catalog"
    })

@app.get("/visualize", response_class=HTMLResponse)
async def visualize(request: Request):
    return templates.TemplateResponse("graph.html", {"request": request, "title": "Knowledge Graph Visualization"})

@app.get("/graph-data")
async def graph_data():
    nodes = {}
    links = []

    def get_node_id(uri):
        return str(uri)

    for s, p, o in rdf_graph:
        s_id = get_node_id(s)
        o_id = get_node_id(o) if isinstance(o, (URIRef)) else None

        if s_id not in nodes:
            nodes[s_id] = {"id": s_id, "label": s_id.split("/")[-1], "group": 1}

        if o_id:
            if o_id not in nodes:
                nodes[o_id] = {"id": o_id, "label": o_id.split("/")[-1], "group": 2}
            links.append({
                "source": s_id,
                "target": o_id,
                "predicate": p.split("#")[-1] if "#" in p else p.split("/")[-1]
            })

    return {"nodes": list(nodes.values()), "links": links}
