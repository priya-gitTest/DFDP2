# 🧠 DFDP2 – DICOM to RDF Processing and Visualization Demo

This project is a **self-contained web application** that demonstrates a complete pipeline for:

- Processing DICOM files
- Extracting key metadata
- Mapping it to semantic ontologies (ROO, SNOMED CT, FOAF, etc.)
- Generating an in-memory **RDF knowledge graph**
- Providing a **web-based interface** for dataset discovery, SPARQL querying, and graph visualization

Built with **Python**, the app uses:
- `FastAPI` for the web server
- `pydicom` for handling DICOM files
- `rdflib` for RDF generation and SPARQL querying
- `D3.js` for frontend graph visualization

---

## 🚀 Features

| Feature | Description |
|--------|-------------|
| 🏥 **DICOM Processing** | Generates 50 mock DICOM files on startup |
| 📑 **Metadata Extraction** | Extracts Patient ID, Study Date, Modality, Accession Number |
| 📚 **Semantic Mapping** | Maps values to ROO, SNOMED CT, and FOAF ontologies |
| 🔗 **RDF Generation** | Builds triples and populates an in-memory knowledge graph |
| 🔍 **SPARQL Endpoint** | Supports SPARQL 1.1 queries via a web form |
| 📂 **Metadata Catalog** | Web interface styled after FAIR Data Platforms (Health DCAT-AP) |
| 🕸️ **Knowledge Graph Visualization** | In-browser graph using force-directed layout |
| ⬆️ **DICOM Upload** | Upload your own DICOMs and enrich the graph dynamically |

---

## 📦 Installation

### ✅ Prerequisites

- Python 3.7+
- pip (Python package manager)

### 🔧 Install Dependencies


```bash
pip install fastapi uvicorn "pydantic[email]" pydicom rdflib requests python-multipart jinja2
```

## ▶️ Running the Application

```bash
#Load the Dicom iamges from Hugging Face Repository and convert them to DICOM files:
python fetch_dicom.py 
# then start the FAST API App.
uvicorn main:app --reload
```
3. Visit: [http://127.0.0.1:8000](http://127.0.0.1:8000)

You’ll see logs like:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started server process [xxxxx]
INFO:     Application startup complete.
```
## 🌐 Web Interface Overview
| Page             | URL          | Description                                     |
| ---------------- | ------------ | ----------------------------------------------- |
| 🏠 **Home**      | `/`          | Upload DICOMs, view summary                     |
| 📚 **Catalog**   | `/catalog`   | View/search processed DICOM datasets            |
| 🌐 **SPARQL**    | `/` (form)   | Query the RDF graph using SPARQL                |
| 🧬 **Visualize** | `/visualize` | Interactive graph of datasets and relationships |

## ⚙️ How It Works

### On Startup

- 50 mock DICOM files are created in `dicom_files/`
- Metadata like `PatientID`, `StudyDate`, and `Modality` are extracted
- Mapped to SNOMED CT and ROO terms
- RDF triples are generated and stored in an in-memory `rdflib.Graph`

### On File Upload

- Uploaded DICOMs are saved to `dicom_uploads/`
- Metadata is extracted and converted into RDF
- The knowledge graph is updated live

## 🧪 SPARQL Query Example

Query all DICOM datasets where the modality is **CT**:

```sparql
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX schema: <http://schema.org/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?dataset ?title ?patientId ?studyDate ?accessionNumber
WHERE {
  ?dataset a <http://health.data.gov.eu/def/dcat-ap/Dataset> .
  ?dataset dcterms:title ?title .
  ?dataset dcterms:subject ?patient .
  ?patient schema:identifier ?patientId .
  ?dataset dcterms:issued ?studyDate .
  ?dataset dcat:theme ?modality .
  ?modality rdfs:label "CT" .
  ?dataset schema:accessionNumber ?accessionNumber .
}
ORDER BY ?studyDate
```

## 📚 Ontologies Used

| Prefix    | URI                                             |
|-----------|--------------------------------------------------|
| `ROO`     | http://www.cancerdata.org/roo/                  |
| `SNOMED`  | http://snomed.info/sct/                         |
| `DCAT`    | http://www.w3.org/ns/dcat#                      |
| `HDCAT`   | http://health.data.gov.eu/def/dcat-ap/         |
| `SCHEMA`  | http://schema.org/                              |
| `FOAF`    | http://xmlns.com/foaf/0.1/                      |
| `DCTERMS` | http://purl.org/dc/terms/                       |
---

## 📁 Directory Structure

```
.
├── main.py             # FastAPI application
├── templates/          # HTML templates (auto-generated)
├── static/             # Static assets (CSS/JS)
├── dicom_files/        # DICOMs downloaded via Script
├── dicom_uploads/      # Uploaded DICOMs via Web Interface
```
---

## 📈 Visualization

At `/visualize`, you'll find a **D3.js-based graph** of the RDF data:

- Nodes are color-coded by type (e.g., Patient, Modality)
- Drag nodes to explore relationships
- Hover over nodes and edges to view URIs and labels

---

## 📌 To-Do / Ideas for Future

- [ ] Persistent RDF store (e.g., Blazegraph, Fuseki)
- [ ] Support for real-world DICOM tags and vocabularies
- [ ] Authentication for upload and SPARQL features
- [ ] Multi-user catalog and permission system

---

## 📄 License

**MIT License**  
Free to use, modify, and distribute with proper attribution.