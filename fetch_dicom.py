import json
import pydicom
from pathlib import Path

# Set up data directory
DATA_DIR = Path("dicom_files")  # change to your folder path

def element_to_dict(elem):
    """
    Convert a single DataElement to a JSON-friendly dict, keeping tag and VR.
    Expands sequences recursively.
    """
    include_tags = {
    # ----------------- Patient Level -----------------
    0x00100010,  # Patient's Name
    0x00100020,  # Patient ID
    0x00100040,  # Patient's Sex
    0x00101010,  # Patient's Age
    0x00102160,  # Ethnic Group
    0x00104000,  # Patient Comments
    0x001021B0,  # Additional Patient History

    # ----------------- Study Level -----------------
    0x0020000D,  # Study Instance UID
    0x00080020,  # Study Date
    0x00080030,  # Study Time
    0x00080050,  # Accession Number
    0x00081030,  # Study Description
    0x00081040,  # Institutional Department Name
    0x00080080,  # Institution Name
    0x00080060,  # Modality
    0x00080070,  # Manufacturer
    0x00081090,  # Manufacturer's Model Name

    # ----------------- Series Level -----------------
    0x0020000E,  # Series Instance UID
    0x00080021,  # Series Date
    0x00080031,  # Series Time
    0x00080060,  # Modality
    0x00200011,  # Series Number
    0x0008103E,  # Series Description

    # ----------------- Image (Instance) Level -----------------
    0x00080018,  # SOP Instance UID
    0x00200013,  # Instance Number
    0x00080022,  # Acquisition Date
    0x00080032,  # Acquisition Time
    0x00200032,  # Image Position (Patient)
    0x00200037,  # Image Orientation (Patient)
    0x00280010,  # Rows
    0x00280011,  # Columns
    # ----------------- Others -----------------
    0x00180010,  # Contrast/Bolus Agent
    0x00180015,  # Body Part Examined
    0x00180022,  # Scan Options
    0x00180050,  # Slice Thickness
    0x00180060,  # KVP
    0x00180090,  # Data Collection Diameter
    0x00181020,  # Software Versions
    0x00181030,  # Protocol Name
    0x00181040,  # Contrast/Bolus Route
    0x00181100,  # Reconstruction Diameter
    0x00181110,  # Distance Source to Detector
    0x00181111,  # Distance Source to Patient
    0x00181120,  # Gantry/Detector Tilt
    0x00181130,  # Table Height
    0x00181140,  # Rotation Direction
    0x00181150,  # Exposure Time
    0x00181151,  # X-Ray Tube Current
    0x00181152,  # Exposure
    0x00181160,  # Filter Type
    0x00181170,  # Generator Power
    0x00181190,  # Focal Spot(s)
    0x00181210,  # Convolution Kernel
    0x00185100,  # Patient Position
    0x00189305,  # Revolution Time
    0x00189306,  # Single Collimation Width
    0x00189307,  # Total Collimation Width
    0x00189309,  # Table Speed
    0x00189310,  # Table Feed per Rotation
    0x00189311,  # Spiral Pitch Factor
    0x00321030,  # Reason for Study
    0x00324000,  # Study Comments,
    0x00100010, 0x00100020, 0x00100040, 0x00101010, 0x00102160, 0x00104000, 0x001021B0,
        0x0020000D, 0x00080020, 0x00080030, 0x00080050, 0x00081030, 0x00081040, 0x00080080,
        0x00080060, 0x00080070, 0x00081090, 0x0020000E, 0x00080021, 0x00080031, 0x00200011,
        0x0008103E, 0x00080018, 0x00200013, 0x00080022, 0x00080032, 0x00200032, 0x00200037,
        0x00280010, 0x00280011, 0x00180010, 0x00180015, 0x00180022, 0x00180050, 0x00180060,
        0x00180090, 0x00181020, 0x00181030, 0x00181040, 0x00181100, 0x00181110, 0x00181111,
        0x00181120, 0x00181130, 0x00181140, 0x00181150, 0x00181151, 0x00181152, 0x00181160,
        0x00181170, 0x00181190, 0x00181210, 0x00185100, 0x00189305, 0x00189306, 0x00189307,
        0x00189309, 0x00189310, 0x00189311, 0x00321030, 0x00324000
}

    if elem.tag not in include_tags:
                    return None
                    unique_tags[tag_str] = name
    #if elem.tag == 0x7FE00010:  # Skip Pixel Data
    #    return None
    
    tag_str = f"({elem.tag.group:04X},{elem.tag.element:04X})"
    
    if elem.VR == "SQ":  # Sequence — expand each item as a dataset
        value = [dataset_to_list(item) for item in elem]
    else:
        val = elem.value
        if isinstance(val, bytes):
            try:
                val = val.decode(errors="ignore")
            except:
                val = str(val)
        elif not isinstance(val, (str, int, float, list, dict, type(None))):
            val = str(val)
        value = val

    return {
        "Tag": tag_str,
        "VR": elem.VR,
        "Name": elem.name,
        "Value": value
    }

def dataset_to_list(ds):
    """
    Convert a Dataset to a list of DataElements, skipping None.
    """
    elements = []
    for elem in ds:
        elem_dict = element_to_dict(elem)
        if elem_dict is not None:
            elements.append(elem_dict)
    return elements

def process_dicom_file(filepath):
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)#Changed stop_before_pixels to True for much faster processing.
        return {
            "FilePath": str(filepath),
            "FileMeta": dataset_to_list(ds.file_meta),
            "Dataset": dataset_to_list(ds)
        }
    except Exception as e:
        return {"FilePath": str(filepath), "Error": str(e)}

def process_dicom_folder(folder_path, output_json):
    all_dicom_data = []
    for filepath in Path(folder_path).rglob("*.dcm"):
        print(f"Processing: {filepath}")
        all_dicom_data.append(process_dicom_file(filepath))
    
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_dicom_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Metadata saved to {output_json}")

# Example run:
if __name__ == "__main__":
    process_dicom_folder(DATA_DIR, "dicom_metadata.json")
