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
| 🏥 **DICOM Processing** | Extracting Metadata from DICOM files picked from TCIA |
| 📑 **Metadata Extraction** | Extracts Patient ID, Study Date, Modality, Accession Number etc |
| 📚 **Semantic Mapping** | Maps values to ROO, SNOMED CT, and FOAF ontologies |
| 🔗 **RDF Generation** | Builds triples and populates an in-memory knowledge graph |
| 🔍 **SPARQL Endpoint** | Supports SPARQL 1.1 queries via a web form |
| 📂 **Metadata Catalog** | Web interface styled after FAIR Data Platforms (Health DCAT-AP) |
| 🕸️ **Knowledge Graph Visualization** | In-browser graph using force-directed layout |


---

## 📦 Installation

### ✅ Prerequisites

- Python 3.7+
- pip (Python package manager)

  ### 🐙 **GitHub Codespaces** *(Recommended)*

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/priya-gitTest/DFDP2)

```bash
# 1. Open in Codespaces (click badge above)

### 🔧 Install Dependencies


```bash
pip install "fastapi[all]" uvicorn  pydicom rdflib requests "python-multipart" Jinja2
```

## ▶️ Running the Application

```bash
#Load the Dicom iamges from Hugging Face Repository and convert them to DICOM files:
python fetch_dicom.py # Generates dicom_metadata.json
python map_dicom_complete.py # Generates dicom_mapped_with_catalog.ttl
# then start the FAST API App.
uvicorn main:app --reload
```
In case you get an error like this : ERROR:    [Errno 98] Address already in use
Fix it using these commands : 
```bash
lsof -i :8000 #uvicorn 18407 codespace    3u  IPv4 257296      0t0  TCP localhost:8000 (LISTEN)
kill -9 XXXX # displayed nos next to uvicorn, so 18407
```
Output : [1]+  Killed                  uvicorn main:app --reload

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

## 🧪 SPARQL Query Example

Query all DICOM datasets where the modality is **CT**:

```sparql
#Query 1
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>

SELECT ?file ?patientId ?studyDate ?modality ?accessionNumber
WHERE {
  ?dataset a dcat:Dataset ;
           dcat:distribution ?file .
  
  ?file dicom:PatientID ?patientId ;
        dicom:SeriesDate ?studyDate ;
        dicom:Modality ?modality ;
        dicom:AccessionNumber ?accessionNumber .
}
ORDER BY ?studyDate
LIMIT 10

#Query 2 : 
PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>

SELECT DISTINCT ?patientId
WHERE {
  ?subject dicom:Manufacturer "GE MEDICAL SYSTEMS" .
  ?subject dicom:PatientID ?patientId .
}

#Query 3
PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>

SELECT DISTINCT ?manufacturer ?modelName
WHERE {
  ?file dicom:Manufacturer ?manufacturer .
  ?file dicom:ManufacturerModelName ?modelName .
}
ORDER BY ?manufacturer ?modelName
#Query 4
PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>
PREFIX roo: <http://www.cancerdata.org/roo/>

SELECT DISTINCT ?patientId ?bodyPart ?age ?sex ?reasonForStudy
WHERE {
  ?subject dicom:PatientID ?patientId .
  ?subject dicom:BodyPartExamined ?bodyPart .

  OPTIONAL { ?subject roo:hasAge ?age . }
  OPTIONAL { ?subject roo:hasSex ?sex . }
  OPTIONAL { ?subject roo:hasReasonForStudy ?reasonForStudy . }
}
#Query 5
PREFIX dicom: <http://dicom.nema.org/resources/ontology/DCM#>
PREFIX dcat: <http://www.w3.org/ns/dcat#>

SELECT ?patientId (COUNT(?file) AS ?numberOfScans)
WHERE {
  ?dataset a dcat:Dataset ;
           dcat:distribution ?file .
  ?file dicom:PatientID ?patientId .
}
GROUP BY ?patientId
ORDER BY ?patientId
```

## 📚 Ontologies Used

| Prefix    | URI                                                   |
|-----------|-------------------------------------------------------|
| `ROO`     | https://www.cancerdata.org/roo-information            |
| `SNOMED`  | https://bioportal.bioontology.org/ontologies/SNOMEDCT |
| `DCAT`    | http://www.w3.org/ns/dcat#                            |
| `FOAF`    | http://xmlns.com/foaf/0.1/                            |
| `dicom`   | http://dicom.nema.org/resources/ontology/DCM          |
| `DCTERMS` | http://purl.org/dc/terms/                             |
---

## 📁 Directory Structure

```
.
├── main.py             # FastAPI application
├── templates/          # HTML templates (auto-generated)
├── static/             # Static assets (CSS/JS)
├── dicom_files/        # DICOMs downloaded via Script
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
