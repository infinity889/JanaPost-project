from __future__ import annotations

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class RawAddressItem(BaseModel):
    id: str
    raw_address: str


class ParsedAddressItem(BaseModel):
    id: str
    raw_address: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    living_area: Optional[str] = None
    street_type: Optional[str] = None
    street_name: Optional[str] = None
    house: Optional[str] = None
    apartment: Optional[str] = None
    entrance: Optional[str] = None
    floor: Optional[str] = None
    landmark: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class BatchParseWrappedRequest(BaseModel):
    records: Optional[List[RawAddressItem]] = None
    items: Optional[List[RawAddressItem]] = None


BatchParsePayload = Union[List[RawAddressItem], BatchParseWrappedRequest]
