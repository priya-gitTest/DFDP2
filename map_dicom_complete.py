import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DC, FOAF
import os

# --- [Namespaces and Mappings remain the same] ---
# Namespaces
DCTERMS = Namespace("http://purl.org/dc/terms/")
ROO = Namespace("http://www.cancerdata.org/roo/")
SNOMED = Namespace("http://snomed.info/sct/")
XSD_NS = Namespace("http://www.w3.org/2001/XMLSchema#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
FOAF_NS = Namespace("http://xmlns.com/foaf/0.1/")
LDP = Namespace("http://www.w3.org/ns/ldp#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
NCIT = Namespace("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#")
DICOM = Namespace("http://dicom.nema.org/resources/ontology/DCM#")
CUSTOM_DICOM = Namespace("http://example.org/dicom/private#")

# SNOMED mapping
snomed_mapping = {
    "THYROID": SNOMED["111160001"],
    "RECTUM": SNOMED["34506005"],
}

# Mapping of DICOM names to properties
mapping = {
    "SOP Instance UID": (DICOM.SOPInstanceUID,),
    "Study Date": (DCTERMS.created,),
    "Series Date": (DICOM.SeriesDate,),
    "Acquisition Date": (DICOM.AcquisitionDate,),
    "Study Time": (DICOM.StudyTime,),
    "Series Time": (DICOM.SeriesTime,),
    "Acquisition Time": (DICOM.AcquisitionTime,),
    "Accession Number": (DICOM.AccessionNumber,),
    "Modality": (DICOM.Modality,),
    "Manufacturer": (DICOM.Manufacturer,),
    "Study Description": (DCTERMS.description,),
    "Series Description": (DICOM.SeriesDescription,),
    "Manufacturer's Model Name": (DICOM.ManufacturerModelName,),
    "Patient's Name": (FOAF_NS.name,),
    "Patient ID": (DICOM.PatientID,),
    "Patient's Sex": (ROO.hasSex,),
    "Patient's Age": (ROO.hasAge,),
    "Additional Patient History": (ROO.hasPatientHistory,),
    "Body Part Examined": (ROO.hasAnatomicSite, DICOM.BodyPartExamined),
    "Scan Options": (DICOM.ScanOptions,),
    "Slice Thickness": (DICOM.SliceThickness,),
    "KVP": (DICOM.KVP,),
    "Data Collection Diameter": (DICOM.DataCollectionDiameter,),
    "Software Versions": (DICOM.SoftwareVersions,),
    "Protocol Name": (DICOM.ProtocolName,),
    "Distance Source to Detector": (DICOM.DistanceSourceToDetector,),
    "Distance Source to Patient": (DICOM.DistanceSourceToPatient,),
    "Gantry/Detector Tilt": (DICOM.GantryDetectorTilt,),
    "Table Height": (DICOM.TableHeight,),
    "Rotation Direction": (DICOM.RotationDirection,),
    "Exposure Time": (DICOM.ExposureTime,),
    "X-Ray Tube Current": (DICOM.XRayTubeCurrent,),
    "Exposure": (DICOM.Exposure,),
    "Filter Type": (DICOM.FilterType,),
    "Generator Power": (DICOM.GeneratorPower,),
    "Focal Spot(s)": (DICOM.FocalSpots,),
    "Convolution Kernel": (DICOM.ConvolutionKernel,),
    "Patient Position": (DICOM.PatientPosition,),
    "Study Instance UID": (DICOM.StudyInstanceUID,),
    "Series Instance UID": (DICOM.SeriesInstanceUID,),
    "Series Number": (DICOM.SeriesNumber,),
    "Instance Number": (DICOM.InstanceNumber,),
    "Image Position (Patient)": (DICOM.ImagePositionPatient,),
    "Image Orientation (Patient)": (DICOM.ImageOrientationPatient,),
    "Rows": (DICOM.Rows,),
    "Columns": (DICOM.Columns,),
    "Reason for Study": (ROO.hasReasonForStudy,),
    "Study Comments": (ROO.hasStudyComment,),
}

def parse_value(value, vr):
    """Convert value based on VR (Value Representation) if needed."""
    if value is None:
        return None
    if vr in ["DS", "IS", "FD", "US"]:
        try:
            # Handle list-like strings e.g., "[0.000, 265.000, 200.000]"
            if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                 return Literal(value) # Keep as a string literal
            return Literal(float(value), datatype=XSD.decimal) if '.' in str(value) else Literal(int(value), datatype=XSD.integer)
        except (ValueError, TypeError):
            return Literal(str(value)) # Fallback to string
    elif vr == "DA":
        s = str(value)
        if len(s) == 8:
            formatted = f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
            return Literal(formatted, datatype=XSD.date)
        return Literal(s)
    elif vr == "TM":
        return Literal(str(value), datatype=XSD.time)
    else:
        return Literal(value)

def json_to_rdf_multiple_catalogs(json_file, output_file):
    g = Graph()

    # --- [Bind namespaces - same as before] ---
    g.bind("dcterms", DCTERMS)
    g.bind("dcat", DCAT)
    g.bind("dicom", DICOM)
    g.bind("foaf", FOAF_NS)
    g.bind("roo", ROO)
    g.bind("snomed", SNOMED)

    with open(json_file) as f:
        data = json.load(f)

    # **MODIFICATION**: Pre-process the flat list to group files by catalog
    catalogs = {}
    for item in data:
        file_path = item.get("FilePath", "")
        # Normalize path separators for consistency
        path_parts = file_path.replace("\\", "/").split('/')
        if len(path_parts) > 1:
            catalog_name = path_parts[1]  # Assumes catalog name is the second part
            if catalog_name not in catalogs:
                catalogs[catalog_name] = []
            catalogs[catalog_name].append(item)

    # **MODIFICATION**: Loop through each pre-processed catalog
    for catalog_name, catalog_data in catalogs.items():
        
        catalog_uri = URIRef(f"http://example.org/catalog/{catalog_name}")
        dataset_uri = URIRef(f"http://example.org/dataset/{catalog_name}")

        g.add((catalog_uri, RDF.type, DCAT.Catalog))
        g.add((catalog_uri, DCTERMS.title, Literal(f"DICOM Collection: {catalog_name}")))
        g.add((catalog_uri, DCAT.dataset, dataset_uri))
        g.add((catalog_uri, DCTERMS.publisher, Literal("Priyanka Test Catalog Publisher")))
        g.add((catalog_uri, DCTERMS.language, Literal("en"))) # Example value for English
        g.add((catalog_uri, DCTERMS.issued, Literal("2025-08-10", datatype=XSD.date))) # Example value for today's date


        g.add((dataset_uri, RDF.type, DCAT.Dataset))
        g.add((dataset_uri, DCTERMS.title, Literal(f"DICOM Files for {catalog_name}")))
        g.add((dataset_uri, DCTERMS.description, Literal(f"A dataset containing all DICOM metadata for catalog {catalog_name}.")))
        
        # Use the Study Instance UID from the first file as a general identifier for the dataset
        if catalog_data:
            first_file_dataset = catalog_data[0].get("Dataset", [])
            study_uid = next((elem.get("Value") for elem in first_file_dataset if elem.get("Name") == "Study Instance UID"), None)
            if study_uid:
                g.add((dataset_uri, DCTERMS.identifier, Literal(study_uid)))

        for item in catalog_data:
            file_path = item.get("FilePath")
            dataset_tags = item.get("Dataset", [])
            
            # Use a clean, unique filename for the subject URI
            subject_id = os.path.basename(file_path)
            subject = URIRef(f"http://example.org/dicom/{catalog_name}_{subject_id}")

            g.add((dataset_uri, DCAT.distribution, subject))
            g.add((subject, RDF.type, DCAT.Distribution))
            g.add((subject, DCTERMS.title, Literal(subject_id)))
            g.add((subject, DCAT.mediaType, Literal("application/dicom")))

            for elem in dataset_tags:
                name = elem.get("Name")
                vr = elem.get("VR")
                value = elem.get("Value")

                if name in mapping and value is not None:
                    props = mapping[name]
                    for prop in props:
                        if prop == ROO.hasAnatomicSite and isinstance(value, str):
                            snomed_uri = snomed_mapping.get(value.upper())
                            g.add((subject, prop, snomed_uri if snomed_uri else Literal(value)))
                        else:
                            lit = parse_value(value, vr)
                            if lit is not None:
                                g.add((subject, prop, lit))

    g.serialize(destination=output_file, format="turtle")

if __name__ == "__main__":
    json_file = "dicom_metadata.json"
    output_file = "dicom_mapped_with_catalog.ttl"
    json_to_rdf_multiple_catalogs(json_file, output_file)
    print(f"RDF mapping with multiple DCAT catalogs written to {output_file}")