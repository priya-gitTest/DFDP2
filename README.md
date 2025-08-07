# DFDP2

DICOM to RDF Processing and Visualization Demo
This project is a self-contained web application that demonstrates a complete pipeline for processing DICOM files, transforming their metadata into a semantic Knowledge Graph, and providing a user-friendly interface to explore the data.

It is built with Python using the FastAPI framework for the web server, pydicom for handling DICOM files, and rdflib for creating and querying RDF data.

Features
DICOM Processing: Automatically processes 50 mock DICOM files on startup to populate the system with initial data.

Metadata Extraction: Pulls key metadata fields like Patient ID, Study Date, and Modality from DICOM headers.

Semantic Mapping: Maps extracted metadata to standard ontologies, including the Radiation Oncology Ontology (ROO) and SNOMED CT.

RDF Generation: Converts the mapped metadata into RDF triples, building an in-memory knowledge graph.

SPARQL Endpoint: Provides a full SPARQL 1.1 compliant endpoint to query the graph.

Metadata Catalog: A web interface styled after the Swiss Fair Data Platform (FDP) and compliant with Health DCAT-AP for dataset discovery.

Knowledge Graph Visualization: An interactive, in-browser visualization of the RDF graph using D3.js.

Extensibility: Allows for the upload of new DICOM files to dynamically extend the knowledge graph.

Setup and Running the Application
1. Prerequisites
Python 3.7+

pip (Python package installer)

2. Installation
First, save the Python code from the Canvas to a file named main.py. Then, open your terminal or command prompt and run the following command to install the necessary Python libraries:

pip install fastapi uvicorn "pydantic[email]" pydicom rdflib requests python-multipart jinja2

3. Running the Server
Once the installation is complete, navigate to the directory where you saved main.py and run the following command:

uvicorn main:app --reload

You should see output indicating that the server is running, similar to this:

INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.

The application is now running and accessible in your web browser.

Exploring the Application
Open your web browser and navigate to http://127.0.0.1:8000.

Home Page (/): This is the main landing page. It provides an overview of the application's features, an interface to test SPARQL queries directly, and a form to upload new DICOM files.

Metadata Catalog (/catalog): This page presents the processed DICOM files as a list of datasets. You can use the search boxes to filter by Modality or Accession Number to discover specific datasets.

Visualize Graph (/visualize): This page provides an interactive, force-directed graph of the RDF data.

Nodes are colored by type (e.g., Patient, Modality, Dataset).

You can click and drag nodes to rearrange the graph and better explore connections.

Hover over nodes and links to see their identifiers and relationships.

How It Works
On Startup: The application automatically creates a dicom_files/ directory with 50 mock DICOM files, processes them, and populates an in-memory RDF graph. It also creates a templates/ directory containing the HTML for the web pages.

File Uploads: When you upload a new DICOM file, it is saved to a dicom_uploads/ directory, and its metadata is immediately processed and added to the live knowledge graph.
