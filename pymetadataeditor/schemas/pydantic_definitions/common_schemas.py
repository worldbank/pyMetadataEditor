from typing import Optional

from pydantic import Field

from pymetadataeditor.tools import SchemaBaseModel


class OriginDescription(SchemaBaseModel):
    harvest_date: Optional[str] = Field(None, description="Harvest date using UTC date format")
    altered: Optional[bool] = Field(
        None,
        description="If the metadata was altered before dissemination",
        title="Metadata altered",
    )
    base_url: Optional[str] = Field(None, description="Base URL of the originating repository")
    identifier: Optional[str] = Field(
        None,
        description="Unique idenifiter of the item from the originating repository",
    )
    date_stamp: Optional[str] = Field(
        None,
        description=(
            "Datestamp (UTC date format) of the metadata record disseminated by the" " originating repository"
        ),
    )
    metadata_namespace: Optional[str] = Field(
        None,
        description=(
            "Metadata namespace URI of the metadata format of the record harvested from" " the originating repository"
        ),
    )


class Producer(SchemaBaseModel):
    name: Optional[str] = Field(None, description="Name (required)", title="Name")
    abbr: Optional[str] = Field(None, title="Abbreviation")
    affiliation: Optional[str] = Field(None, title="Affiliation")
    role: Optional[str] = Field(None, title="Role")


class ProvenanceSchema(SchemaBaseModel):
    """
    Provenance of metadata based on the OAI provenance schema (http://www.openarchives.org/OAI/2.0/provenance.xsd)
    """

    origin_description: Optional[OriginDescription] = Field(None, title="Origin description")


class Tag(SchemaBaseModel):
    tag: Optional[str] = Field(None, title="Tag")
    tag_group: Optional[str] = Field(None, title="Tag group")
