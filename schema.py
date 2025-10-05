#===DateTime Format==============================

import re
from pydantic import BaseModel, field_validator
from datetime import datetime

thai_months = {
    "ม.ค.": "Jan", "ก.พ.": "Feb", "มี.ค.": "Mar", "เม.ย.": "Apr",
    "พ.ค.": "May", "มิ.ย.": "Jun", "ก.ค.": "Jul", "ส.ค.": "Aug",
    "ก.ย.": "Sep", "ต.ค.": "Oct", "พ.ย.": "Nov", "ธ.ค.": "Dec",
    "มกราคม": "January", "กุมภาพันธ์": "February", "มีนาคม": "March", "เมษายน": "April",
    "พฤษภาคม": "May", "มิถุนายน": "June", "กรกฎาคม": "July", "สิงหาคม": "August",
    "กันยายน": "September", "ตุลาคม": "October", "พฤศจิกายน": "November", "ธันวาคม": "December"
}

class DateTimeForm(BaseModel):
    """
    The way the datetime should be structured and formatted.
    """
    
    datetime: str

    @field_validator('datetime', mode='before')
    @classmethod
    def validate_datetime(cls, value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')

        if value.lower() in ('now', 'today'):
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Replace Thai month to English
        for th, en in thai_months.items():
            value = re.sub(th, en, value)

        # Replace '.' with ':' in time
        value = re.sub(r'(\d{1,2})\.(\d{2})', r'\1:\2', value)

        # Extract date/time parts with multiple patterns
        patterns = [
            ("%d/%m/%Y %H:%M", True),
            ("%Y/%m/%d %H:%M", True),
            ("%d-%m-%Y %H:%M", True),
            ("%Y-%m-%d %H:%M", True),
            ("%d %b %Y %H:%M", True),
            ("%d %B %Y %H:%M", True),
            ("%b %d, %Y %H:%M", True),
            ("%d-%b-%Y %H:%M", True),
        ]

        for fmt, allow_be in patterns:
            try:
                dt = datetime.strptime(value, fmt)
                if allow_be and dt.year > 2500:
                    dt = dt.replace(year=dt.year - 543)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        raise ValueError("The date must be in format 'YYYY-MM-DD HH:MM:SS', 'now', 'today', or common Thai/English formats with '.' or ':' time")

#===Processes Format=========================

from pydantic import BaseModel,Field,field_validator
import re

class ProcessForm(BaseModel):
    """
    The way the 3 main processes should be structured and formatted.
    """
    proc: str = Field(
        ..., 
        description="Classify 3 main processes"
    )

    @field_validator("proc")
    def var_proc(cls,value):
        value = value.lower()
        if value not in {"hauling", "stock", "usage"}:
            raise ValueError("The processes should be in 'Hauling','Stock','Usage'")
        return value
    
#===Family Steel Format=========================

from pydantic import BaseModel,field_validator
import re

class FamilyForm(BaseModel):
    """
    The way the steel family should be structured and formatted.
    """
    family: str

    @field_validator("family")
    def var_family(cls, value):
        v = value.lower()

        # กรองคำที่ user น่าจะพิมพ์มา
        if any(kw in v for kw in ["shs", "square", "sq", "sqs", "sqr"]):
            return "SHS - Square Hollow Section"
        elif any(kw in v for kw in ["rhs", "rectangle", "rect", "rec"]):
            return "RHS - Rectangular Hollow Section"
        else:
            raise ValueError(
                "The steel family must refer to 'SHS - Square Hollow Section' or 'RHS - Rectangular Hollow Section'"
            )

#Roof Structure Format=========================

from pydantic import BaseModel, Field, field_validator

class RoofForm(BaseModel):
    """
    The way the roof structure element should be structured and formatted.
    """
    roof: str = Field(
        ..., 
        description="The each of roof structure element"
    )

    @field_validator("roof")
    def var_roof(cls, value):
        value = value.lower().strip()

        mapping = {
            "ridge": ["อกไก่", "ridge"],
            "king post": ["ดั้ง", "king post"],
            "hip rafter": ["ตะเข้สัน", "hip"], 
            "valley rafter": ["ตะเข้ราง", "valley"],
            "rafter": ["จันทัน", "rafter"], 
            "stud beam": ["อะเส", "stud"],
            "tie beam": ["ขื่อ", "tie"],
            "columns": ["เสา", "column", "columns"],
            "-": ["-"]
        }

        for standard_name, keywords in mapping.items():
            if any(kw in value for kw in keywords):
                return standard_name  # <-- แก้ไข: ลบ .title() ออก

        raise ValueError("The roof structure element is invalid. Please use valid terms like ขื่อ, จันทัน, etc.")
    
#===Flow Format==========================

from pydantic import BaseModel,Field,field_validator
import re

class FlowForm(BaseModel):
    """
    The way the flow of materials should be structured and formatted.
    """
    flow: str = Field(
        ..., 
        description="The flow of materials"
    )

    @field_validator("flow")
    def var_flow(cls,value):
        names = {"in","out","-"}
        v = value.lower()
        if v not in names:
            raise ValueError("The flow format wrong!")
        return v
    
#===Dimensions section Format==========================

from pydantic import BaseModel,Field,field_validator
import re

class DimForm(BaseModel):
    """
    The way the cross-sectional dimensions of the material should be structured and formatted.
    """
    dim: str = Field(
        ..., 
        description="The dimensions of steel section"
    )

    @field_validator("dim")
    def validate_dim(cls, value):
        # regex ที่รองรับทั้งจำนวนเต็มและทศนิยม เช่น 100x100x6 หรือ 100x100x6.5
        if not re.match(r'^\d{2,3}x\d{2,3}x\d{1,2}(\.\d{1,2})?$', value):
            raise ValueError("The dimensions should be in format 'WxHxT' (e.g., '100x100x6' or '100x100x6.5')")
        return value