import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DC, FOAF, DCAT
import os
from collections import defaultdict

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
    g.bind("dcat", DCAT)
    g.bind("dcterms", DCTERMS)
    g.bind("dicom", DICOM)
    g.bind("foaf", FOAF)
    g.bind("roo", ROO)
    g.bind("snomed", SNOMED)
    # ... bind other namespaces if you have them ...

    with open(json_file) as f:
        data = json.load(f)

    # --- Pre-processing Logic ---
    catalogs = defaultdict(lambda: defaultdict(list))
    for item in data:
        file_path = item.get("FilePath", "")
        path_parts = file_path.replace("\\", "/").split('/')
        
        if len(path_parts) > 1:
            catalog_name = path_parts[1]
            study_uid = "unknown_study"
            for elem in item.get("Dataset", []):
                if elem.get("Name") == "Study Instance UID":
                    study_uid = elem.get("Value")
                    break
            catalogs[catalog_name][study_uid].append(item)

    # --- RDF Generation Logic ---
    for catalog_name, studies in catalogs.items():
        catalog_uri = URIRef(f"http://example.org/catalog/{catalog_name}")
        g.add((catalog_uri, RDF.type, DCAT.Catalog))
        g.add((catalog_uri, DCTERMS.title, Literal(f"DICOM Collection: {catalog_name}")))
        g.add((catalog_uri, DCTERMS.publisher, Literal("Priyanka Demo Catalog Publisher Name")))
        g.add((catalog_uri, DCTERMS.issued, Literal("2025-08-10", datatype=XSD.date)))
        g.add((catalog_uri, DCTERMS.language, Literal("en")))

        for study_uid, files_in_study in studies.items():
            dataset_uri = URIRef(f"http://example.org/dataset/{study_uid}")
            g.add((catalog_uri, DCAT.dataset, dataset_uri))

            g.add((dataset_uri, RDF.type, DCAT.Dataset))
            g.add((dataset_uri, DCTERMS.identifier, Literal(study_uid)))

            if files_in_study:
                first_file_ds = files_in_study[0].get("Dataset", [])
                study_desc = next((e.get("Value") for e in first_file_ds if e.get("Name") == "Study Description"), f"Study {study_uid}")
                g.add((dataset_uri, DCTERMS.title, Literal(study_desc)))

            for item in files_in_study:
                file_path = item.get("FilePath")
                dataset_tags = item.get("Dataset", [])
                
                # **MODIFICATION**: Create a unique ID from the full path
                # This prevents filename collisions between different subfolders.
                unique_file_id = file_path.replace('/', '_').replace('\\', '_')
                subject_uri = URIRef(f"http://example.org/dicom/{unique_file_id}")

                g.add((dataset_uri, DCAT.distribution, subject_uri))
                g.add((subject_uri, RDF.type, DCAT.Distribution))
                g.add((subject_uri, DCTERMS.title, Literal(os.path.basename(file_path))))
                g.add((subject_uri, DCAT.mediaType, Literal("application/dicom")))

                for elem in dataset_tags:
                    name, vr, value = elem.get("Name"), elem.get("VR"), elem.get("Value")
                    if name in mapping and value is not None:
                        props = mapping[name]
                        for prop in props:
                            lit = parse_value(value, vr)
                            if lit:
                                g.add((subject_uri, prop, lit))
                                
    g.serialize(destination=output_file, format="turtle")


if __name__ == "__main__":
    json_file = "dicom_metadata.json"
    output_file = "dicom_mapped_with_catalog.ttl"
    json_to_rdf_multiple_catalogs(json_file, output_file)
    print(f"RDF mapping written to {output_file}")