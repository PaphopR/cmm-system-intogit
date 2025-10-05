from dotenv import load_dotenv
load_dotenv()
import os
from schema import DateTimeForm, FamilyForm, FlowForm, DimForm, ProcessForm, RoofForm

#Object Detection Tool with YOLOv11

import requests
from typing import Annotated
from PIL import ImageDraw, Image
from io import BytesIO
import io
import base64

YOLO_URL_API = os.getenv("YOLO_URL_API")
YOLO_MODEL_API = os.getenv("YOLO_MODEL_API")

def objectdetection(image_path: str):    
    """

        This tool is designed to detect objects in the image provided by the user, either as type <class 'PIL.JpegImagePlugin.JpegImageFile'> from user input. 
        Once detected, it counts the number of those objects in the image and returns the results that include the number and the image detected result.

        The primary purpose of this tool is to detect the end-face (cross-sectional view) of steel hollow sections, 
    such as Square Hollow Sections (SHS) or Rectangular Hollow Sections (RHS), from the image given by the user.
    After detection, it counts the number of these sections and returns the results. This count is intended to 
    be passed into the 'quantity' parameter in the 'datacollection()' function.

        Step of using this tool:
            step 1: Upload an image of the steel hollow section (SHS/RHS).
            step 2: The tool will process the image and detect the number of sections. And then process in
                    the image with the bounding boxes.
            step 3: The tool will return the number of sections detected and the image with the bounding boxes 
                    that detected on steel hollow sections.
            step 4: 4.1) Send the number of sections detected to the 'quantity' parameter in the 'datacollection()'.
                    4.2) Send the image of sections detected to the streamlit app for display.

    """

    if not os.path.exists(image_path):
        return None, "❌ Image path not found."

    image = Image.open(image_path).convert("RGB")
    image_bytes = BytesIO()
    image.save(image_bytes, format="JPEG")
    image_bytes.seek(0)

    headers = {"x-api-key": YOLO_URL_API}
    data = {"model": YOLO_MODEL_API, "imgsz": 640, "conf": 0.25, "iou": 0.45}
    files = {"file": ("image.jpg", image_bytes, "image/jpeg")}

    try:
        response = requests.post("https://predict.ultralytics.com", headers=headers, data=data, files=files)
        response.raise_for_status()
        result_json = response.json()
    except Exception as e:
        return None, str(e)

    results = []
    for img_data in result_json.get("images", []):
        results.extend(img_data.get("results", []))

    draw = ImageDraw.Draw(image)
    for obj in results:
        box = obj.get("box", {})
        x1, y1, x2, y2 = box.get("x1", 0), box.get("y1", 0), box.get("x2", 0), box.get("y2", 0)
        draw.rectangle([x1, y1, x2, y2], outline="lime", width=2)

    return image, len(results)

#Data Collection Tool with Supabase

from typing import Dict
from supabase import create_client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def datacollection(
    datetime: DateTimeForm,
    family: FamilyForm,
    flow: FlowForm,
    dimension: DimForm,
    length: float,
    quantity: int,
    process: ProcessForm,
    element: RoofForm,
    description: str
) -> dict:
    """

        This tool is designed to extract and record key information from user inputs written in natural language, 
    without relying on fixed templates or forms.
        Once extracted, each key must conform to a predefined structure by mapping to a specific class based on 'BaseModel', 
    ensuring the data is properly allocated and validated.        
    
        The primary purpose of this tool is to track the flow of steel hollow section materials (specifically square and rectangular types) 
    across three construction phases: (1) Hauling/Transportation, (2) Stock/Inventory/Store/Warehouse, and (3) Usage/Installation.

        The tool must be able to interpret dynamic user inputs — such as descriptions, reports, or free-form messages — 
    and convert them into structured data.

        Each extracted key is associated with a corresponding subclass of 'BaseModel', as defined below:

        - Key "datetime" -> class DateTimeForm(BaseModel):
            Defines how datetime values should be extracted and formatted from the user input.

        - Key "process" -> class ProcessForm(BaseModel):
            Defines how the construction process type is extracted and formatted from the input.

        - Key "flow" -> class FlowForm(BaseModel):
            Defines flow-related values, active **only** in the `"Stock/Inventory/Store/Warehouse"` process.  
            For any other process, set this key's value to "-".

        - Key "family" -> class FamilyForm(BaseModel):
            Extracts and formats the steel material type (e.g., Square Hollow Section, Rectangular Hollow Section) from user input.

        - Key "dimension" -> class DimForm(BaseModel):
            Extracts and formats the cross-sectional dimensions of the material.

        - Key "length":
            Extracts and formats the length of the steel material from user input.

        - Key "quantity":
            - Extracts the number of steel materials. This value can be obtained in one of two ways:  
              (1) via the 'objectdetection()' function, or  
              (2) directly from user input.
            - Whatever situation, Only process 'stock' in flow 'out' process, If user input value the quantity, Always HAVE TO transfer minus value (e.g. '1' -> '-1').

        - Key "element" -> class RoofForm(BaseModel):
            Extracts and formats element-related values, active **only** in the `"Usage/Installation"` process.  
            For any other process, set this key's value to "-".

        - Key "description":
            Captures additional information from the user input that does not fall under any other defined key.  
            Active **only** in the `"Usage/Installation"` process. For other processes, set this value to "-".

        All extracted data will be stored in an SQL database (this tool is linked to **Supabase**, using PostgreSQL via API),
    where each key maps to a predefined column.

        **Important:** 
            (1) The entire workflow of this tool operates in a **step-by-step** manner.
            (2) As this tool is designed to handle dynamic inputs, it have to support both Thai and English language.
            
    """
    
    data = {
        "datetime": str(datetime.datetime),
        "process": process.proc,
        "flow": flow.flow,
        "family": family.family,
        "dimension": dimension.dim,
        "length": length,
        "quantity": quantity,
        "element": element.roof,
        "description": description
    }
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    table_name = "case_database"
    
    supabase.table(table_name).insert(data).execute()
    print("\n«  Data Collected!  »\n")

    return data
