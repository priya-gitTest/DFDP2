import os
from pathlib import Path
import numpy as np
from datasets import load_dataset
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
import datetime
from PIL import Image

# Set up data directory
DATA_DIR = Path("dicom_files")
DATA_DIR.mkdir(exist_ok=True)

def create_dicom_from_image(image_array, filename, patient_id="PATIENT001", study_id="STUDY001"):
    """
    Create a DICOM file from an image array
    """
    # Create a new DICOM dataset
    ds = Dataset()
    
    # Set the transfer syntax
    ds.file_meta = Dataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.7"  # Secondary Capture Image Storage
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid()
    ds.file_meta.ImplementationClassUID = generate_uid()
    
    # Set required DICOM attributes
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.7"
    ds.SOPInstanceUID = generate_uid()
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    
    # Patient information
    ds.PatientName = f"Patient^{patient_id}"
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19900101"
    ds.PatientSex = "O"  # Other
    
    # Study information
    ds.StudyID = study_id
    ds.StudyDate = datetime.datetime.now().strftime("%Y%m%d")
    ds.StudyTime = datetime.datetime.now().strftime("%H%M%S")
    ds.AccessionNumber = ""
    
    # Series information
    ds.SeriesNumber = "1"
    ds.SeriesDate = datetime.datetime.now().strftime("%Y%m%d")
    ds.SeriesTime = datetime.datetime.now().strftime("%H%M%S")
    ds.Modality = "OT"  # Other
    
    # Instance information
    ds.InstanceNumber = "1"
    ds.ContentDate = datetime.datetime.now().strftime("%Y%m%d")
    ds.ContentTime = datetime.datetime.now().strftime("%H%M%S")
    
    # Image information
    if len(image_array.shape) == 2:  # Grayscale
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        pixel_array = image_array
    elif len(image_array.shape) == 3:  # Color
        ds.SamplesPerPixel = 3
        ds.PhotometricInterpretation = "RGB"
        ds.PlanarConfiguration = 0
        pixel_array = image_array
    
    ds.Rows, ds.Columns = pixel_array.shape[:2]
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    
    # Set pixel data
    if len(pixel_array.shape) == 3:
        ds.PixelData = pixel_array.tobytes()
    else:
        ds.PixelData = pixel_array.tobytes()
    
    # Save as DICOM
    ds.save_as(filename, write_like_original=False)

def download_and_convert_to_dicom():
    """Download images from Hugging Face and convert to DICOM format"""
    
    print("Loading dataset from Hugging Face...")
    print("-" * 50)
    
    try:
        # Load the dataset
        ds = load_dataset("TrainingDataPro/dicom-brain-dataset")
        dataset = ds['train'] if 'train' in ds else list(ds.values())[0]
        
        print(f"Dataset loaded! Total samples: {len(dataset)}")
        
        # Limit to 50 files
        max_files = min(50, len(dataset))
        converted_count = 0
        
        print(f"\nConverting first {max_files} images to DICOM format...")
        print("-" * 50)
        
        for i in range(max_files):
            try:
                sample = dataset[i]
                
                # Find the image data
                image_data = None
                if 'image' in sample:
                    image_data = sample['image']
                elif 'scan' in sample:
                    image_data = sample['scan']
                
                if image_data is None:
                    print(f"[{i+1:2d}/{max_files}] No image data found in sample {i}")
                    continue
                
                # Create DICOM filename
                dicom_filename = f"brain_scan_{i+1:03d}.dcm"
                dicom_filepath = DATA_DIR / dicom_filename
                
                # Skip if file already exists
                if dicom_filepath.exists():
                    print(f"[{i+1:2d}/{max_files}] {dicom_filename} already exists, skipping...")
                    converted_count += 1
                    continue
                
                print(f"[{i+1:2d}/{max_files}] Converting {dicom_filename}...", end=" ")
                
                # Convert PIL Image to numpy array
                if hasattr(image_data, 'convert'):  # PIL Image
                    # Convert to grayscale for DICOM compatibility
                    image_array = np.array(image_data.convert('L'))
                elif isinstance(image_data, np.ndarray):
                    image_array = image_data
                else:
                    image_array = np.array(image_data)
                
                # Ensure proper data type
                if image_array.dtype != np.uint8:
                    image_array = ((image_array - image_array.min()) / 
                                  (image_array.max() - image_array.min()) * 255).astype(np.uint8)
                
                # Create DICOM file
                create_dicom_from_image(
                    image_array, 
                    dicom_filepath,
                    patient_id=f"PAT{i+1:03d}",
                    study_id=f"STU{i+1:03d}"
                )
                
                file_size = dicom_filepath.stat().st_size
                print(f"✓ ({file_size:,} bytes)")
                converted_count += 1
                
            except Exception as e:
                print(f"[{i+1:2d}/{max_files}] ✗ Error: {str(e)}")
                continue
        
        print("-" * 50)
        print(f"Conversion complete!")
        print(f"Successfully converted: {converted_count} files to DICOM format")
        
        return converted_count
        
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        return 0

def read_dicom_file(filepath):
    """Read and display information about a DICOM file"""
    try:
        ds = pydicom.dcmread(filepath)
        
        print(f"\nDICOM File: {filepath.name}")
        print("-" * 40)
        print(f"Patient Name: {getattr(ds, 'PatientName', 'N/A')}")
        print(f"Patient ID: {getattr(ds, 'PatientID', 'N/A')}")
        print(f"Modality: {getattr(ds, 'Modality', 'N/A')}")
        print(f"Study Date: {getattr(ds, 'StudyDate', 'N/A')}")
        print(f"Image Size: {getattr(ds, 'Rows', 'N/A')} x {getattr(ds, 'Columns', 'N/A')}")
        print(f"Pixel Data Shape: {ds.pixel_array.shape if hasattr(ds, 'pixel_array') else 'N/A'}")
        
        return ds
        
    except Exception as e:
        print(f"Error reading DICOM file {filepath}: {e}")
        return None

def list_dicom_files():
    """List all DICOM files and show their info"""
    dicom_files = list(DATA_DIR.glob("*.dcm"))
    
    if not dicom_files:
        print("No DICOM files found in the directory.")
        return
    
    print(f"\nFound {len(dicom_files)} DICOM files:")
    print("=" * 60)
    
    total_size = 0
    for file_path in sorted(dicom_files):
        size = file_path.stat().st_size
        total_size += size
        
        # Try to read basic info
        try:
            ds = pydicom.dcmread(file_path, stop_before_pixels=True)  # Fast read
            patient_id = getattr(ds, 'PatientID', 'Unknown')
            modality = getattr(ds, 'Modality', 'Unknown')
            print(f"{file_path.name:<25} {size:>8,} bytes  Patient: {patient_id}  Modality: {modality}")
        except:
            print(f"{file_path.name:<25} {size:>8,} bytes  [Error reading metadata]")
    
    print("-" * 60)
    print(f"Total: {len(dicom_files)} DICOM files, {total_size:,} bytes")

def test_dicom_reading():
    """Test reading the first DICOM file"""
    dicom_files = list(DATA_DIR.glob("*.dcm"))
    
    if dicom_files:
        print("\nTesting DICOM file reading:")
        print("=" * 50)
        first_dicom = dicom_files[0]
        ds = read_dicom_file(first_dicom)
        
        if ds and hasattr(ds, 'pixel_array'):
            pixel_data = ds.pixel_array
            print(f"Pixel data type: {pixel_data.dtype}")
            print(f"Pixel data range: {pixel_data.min()} to {pixel_data.max()}")
            print(f"✓ Successfully read DICOM pixel data!")
    else:
        print("No DICOM files found to test.")

if __name__ == "__main__":
    try:
        print("Hugging Face to DICOM Converter")
        print("=" * 50)
        
        # Convert images to DICOM format
        converted = download_and_convert_to_dicom()
        
        # List the created DICOM files
        list_dicom_files()
        
        # Test reading one DICOM file
        test_dicom_reading()
        
        if converted > 0:
            print(f"\n✓ Successfully created {converted} DICOM files")
            print(f"Files saved to: {DATA_DIR.absolute()}")
            print("\nThese are now proper DICOM files that can be read with pydicom!")
        else:
            print("\n✗ No files were converted successfully")
            print("Make sure you have installed: pip install pydicom datasets pillow numpy")
            
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user")
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
