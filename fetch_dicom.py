import os
import json
from pathlib import Path
import pydicom
from pydicom.tag import Tag


# Set up data directory
DATA_DIR = Path("dicom_files")  # change to your folder path

def element_to_dict(elem):
    """
    Convert a single DataElement to a JSON-friendly dict, keeping tag and VR.
    """

    # Skip Pixel Data tag
    if elem.tag == 0x7FE00010:
        return None
    
    tag_str = f"({elem.tag.group:04X},{elem.tag.element:04X})"
    
    # Handle sequences recursively
    if elem.VR == "SQ":
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
        "Name": elem.name,  # Works across pydicom versions
        "Value": value
    }

def dataset_to_list(ds):
    """
    Convert a Dataset to a list of DataElements preserving order.
    """
    elements = []
    for elem in ds:
        elements.append(element_to_dict(elem))
    return elements

def process_dicom_file(filepath):
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=False, force=True)

        file_meta_list = dataset_to_list(ds.file_meta)
        dataset_list = dataset_to_list(ds)

        return {
            "FilePath": str(filepath),
            "FileMeta": file_meta_list,
            "Dataset": dataset_list
        }
    except Exception as e:
        return {"FilePath": str(filepath), "Error": str(e)}

def process_dicom_folder(folder_path, output_json):
    all_dicom_data = []

    for filepath in folder_path.rglob("*.dcm"):  # recursive search
        print(f"Processing: {filepath}")
        dicom_data = process_dicom_file(filepath)
        all_dicom_data.append(dicom_data)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_dicom_data, f, indent=4, ensure_ascii=False)

    print(f"✅ Metadata saved to {output_json}")

# Example run
process_dicom_folder(DATA_DIR, "dicom_metadata.json")
