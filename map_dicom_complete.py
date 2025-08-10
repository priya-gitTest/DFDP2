import json
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DC, FOAF

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

# SNOMED mapping for certain terms (expand as needed)
snomed_mapping = {
    "THYROID": SNOMED["111160001"],  # Example SNOMED code for Thyroid
}

# Mapping of DICOM names to properties, including multi-namespace where appropriate
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
    if vr in ["DS", "IS"]:
        try:
            return Literal(float(value), datatype=XSD.decimal) if '.' in str(value) else Literal(int(value), datatype=XSD.integer)
        except:
            return Literal(value)
    elif vr == "DA":  # Date
        # Format from yyyymmdd to yyyy-mm-dd
        s = str(value)
        if len(s) == 8:
            formatted = f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
            return Literal(formatted, datatype=XSD.date)
        return Literal(value)
    elif vr == "TM":  # Time (leave as string)
        return Literal(value, datatype=XSD.time)
    else:
        return Literal(value)

def json_to_rdf(json_file, output_file):
    g = Graph()

    # Bind namespaces
    g.bind("dcterms", DCTERMS)
    g.bind("rdfs", RDFS)
    g.bind("roo", ROO)
    g.bind("snomed", SNOMED)
    g.bind("xsd", XSD_NS)
    g.bind("dcat", DCAT)
    g.bind("foaf", FOAF_NS)
    g.bind("ldp", LDP)
    g.bind("owl", OWL)
    g.bind("ncit", NCIT)
    g.bind("dicom", DICOM)

    with open(json_file) as f:
        data = json.load(f)

    catalog_uri = URIRef("http://example.org/catalog")
    dataset_uri = URIRef("http://example.org/dataset/dicom_dataset")

    # Create DCAT catalog and dataset
    g.add((catalog_uri, RDF.type, DCAT.Catalog))
    g.add((catalog_uri, DCAT.dataset, dataset_uri))

    g.add((dataset_uri, RDF.type, DCAT.Dataset))
    g.add((dataset_uri, DCTERMS.title, Literal("DICOM Metadata Dataset")))
    g.add((dataset_uri, DCTERMS.description, Literal("A dataset containing DICOM metadata mapped to ontologies.")))

    for item in data:
        file_path = item.get("FilePath")
        dataset = item.get("Dataset", [])

        # Subject URI for each DICOM file
        subject = URIRef(f"http://example.org/dicom/{file_path.replace('/', '_')}")

        g.add((dataset_uri, DCAT.distribution, subject))  # Link file as distribution of dataset
        g.add((subject, RDF.type, DICOM.DICOMFile))

        for elem in dataset:
            name = elem.get("Name")
            vr = elem.get("VR")
            value = elem.get("Value")

            if name in mapping and value is not None:
                props = mapping[name]

                for prop in props:
                    # Special case: map certain body part text values to SNOMED URI if possible
                    if prop == ROO.hasAnatomicSite and isinstance(value, str):
                        snomed_uri = snomed_mapping.get(value.upper())
                        if snomed_uri:
                            g.add((subject, prop, snomed_uri))
                        else:
                            g.add((subject, prop, Literal(value)))
                    else:
                        lit = parse_value(value, vr)
                        if lit is not None:
                            g.add((subject, prop, lit))

    g.serialize(destination=output_file, format="turtle")

if __name__ == "__main__":
    json_file = "dicom_metadata.json"   # Your JSON file path here
    output_file = "dicom_mapped_with_catalog.ttl"
    json_to_rdf(json_file, output_file)
    print(f"RDF mapping with DCAT catalog written to {output_file}")
