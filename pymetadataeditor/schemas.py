from typing import List, Optional

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class SchemaBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    def __setitem__(self, key, value):
        setattr(self, key, value)


class Producer(SchemaBaseModel):
    name: Optional[str] = None
    abbr: Optional[str] = None
    affiliation: Optional[str] = None
    role: Optional[str] = None


class VersionStatement(SchemaBaseModel):
    version: Optional[str] = None
    version_date: Optional[str] = None
    version_resp: Optional[str] = None
    version_notes: Optional[str] = None


class AuthoringEntity(SchemaBaseModel):
    name: str
    affiliation: Optional[str] = None
    abbreviation: Optional[str] = None
    email: Optional[str] = None
    uri: Optional[str] = None


class Alias(SchemaBaseModel):
    """
    The documentation https://metadataeditorqa.worldbank.org/api-documentation/editor/#operation/createTimeseries
    says that this is not required, but if aliases is not empty then it must contain some information
    """

    alias: str


class AlternateIdentifier(SchemaBaseModel):
    identifier: str
    name: Optional[str] = None
    database: Optional[str] = None
    uri: Optional[str] = None
    notes: Optional[str] = None


class Language(SchemaBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class Dimension(SchemaBaseModel):
    name: Optional[str] = None
    label: str
    description: Optional[str] = None


class Reference(SchemaBaseModel):
    source: Optional[str] = None
    uri: AnyUrl
    note: Optional[str] = None


class Concept(SchemaBaseModel):
    name: str
    definition: Optional[str] = None
    uri: Optional[AnyUrl] = None


class DataCollection(SchemaBaseModel):
    data_source: Optional[str] = None
    method: Optional[str] = None
    period: Optional[str] = None
    note: Optional[str] = None
    uri: Optional[str] = None


class Vocabulary(SchemaBaseModel):
    id: Optional[str] = None
    name: str
    parent_id: Optional[str] = None
    vocabulary: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Mandate(SchemaBaseModel):
    mandate: Optional[str] = None
    uri: Optional[AnyUrl] = None


class TimePeriod(SchemaBaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    notes: Optional[str] = None


class RefCountry(SchemaBaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class GeographicUnit(SchemaBaseModel):
    name: str
    code: Optional[str] = None
    type: Optional[str] = None


class BoundingBox(SchemaBaseModel):
    """If a bounding box is given, aren't all the fields required?
    They're not listed as required on
        https://metadataeditorqa.worldbank.org/api-documentation/editor/#operation/createTimeseries
    Also, on the site, the bounding box is a square but these names suggest a diamond, is that right??
    """

    west: Optional[str] = None
    east: Optional[str] = None
    south: Optional[str] = None
    north: Optional[str] = None


class Link(SchemaBaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    uri: Optional[AnyUrl] = None


class ApiDocumentation(SchemaBaseModel):
    description: Optional[str] = None
    uri: Optional[AnyUrl] = None


class OtherIdentifier(SchemaBaseModel):
    """
    why does this field contain an 'identifier' when authorid contains an 'id'
    Shouldn't we be consistent and call things one or the other?
    Of course, it's often more important not to make breaking changes...
    """

    type: Optional[str] = None
    identifier: Optional[str] = None


class AuthorId(SchemaBaseModel):
    type: Optional[str] = None
    id: Optional[str] = None


class Author(SchemaBaseModel):
    first_name: Optional[str] = None
    initial: Optional[str] = None
    last_name: Optional[str] = None
    affiliation: Optional[str] = None
    author_id: Optional[List[AuthorId]] = None
    full_name: Optional[str] = None


class Dataset(SchemaBaseModel):
    idno: Optional[str] = None
    title: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Source(SchemaBaseModel):
    idno: Optional[str] = None
    other_identifiers: Optional[List[OtherIdentifier]] = None
    type: Optional[str] = None
    name: str
    organization: Optional[str] = None
    authors: Optional[List[Author]] = None
    datasets: Optional[List[Dataset]] = None
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    uri: Optional[AnyUrl] = None
    access_date: Optional[str] = None
    note: Optional[str] = None


class Keyword(SchemaBaseModel):
    name: str
    vocabulary: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Acronym(SchemaBaseModel):
    acronym: str
    expansion: str
    occurrence: Optional[int] = None


class Erratum(SchemaBaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Acknowledgement(SchemaBaseModel):
    name: Optional[str] = None
    affiliation: Optional[str] = None
    role: Optional[str] = None


class Note(SchemaBaseModel):
    note: Optional[str] = None
    type: Optional[str] = None
    uri: Optional[AnyUrl] = None


class RelatedIndicator(SchemaBaseModel):
    code: Optional[str] = None
    label: Optional[str] = None
    uri: Optional[AnyUrl] = None
    relationship: Optional[str] = None
    type: Optional[str] = None


class Compliance(SchemaBaseModel):
    standard: str
    abbreviation: Optional[str] = None
    custodian: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Framework(SchemaBaseModel):
    name: str
    abbreviation: Optional[str] = None
    custodian: Optional[str] = None
    description: Optional[str] = None
    goal_id: Optional[str] = None
    goal_name: Optional[str] = None
    goal_description: Optional[str] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    target_description: Optional[str] = None
    indicator_id: Optional[str] = None
    indicator_name: Optional[str] = None
    indicator_description: Optional[str] = None
    uri: Optional[AnyUrl] = None
    notes: Optional[str] = None


class SeriesGroup(SchemaBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    uri: Optional[AnyUrl] = None


class Contact(SchemaBaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    position: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    uri: Optional[AnyUrl] = None


class MetadataInformation(SchemaBaseModel):
    title: Optional[str] = None
    idno: Optional[str] = None
    producers: Optional[List[Producer]] = None
    prod_date: Optional[str] = None
    version_statement: Optional[VersionStatement] = None


class SeriesDescription(SchemaBaseModel):
    idno: str
    doi: Optional[str] = None
    name: str
    display_name: Optional[str] = None
    authoring_entity: Optional[List[AuthoringEntity]] = None
    database_id: Optional[str] = None
    database_name: Optional[str] = None
    date_last_update: Optional[str] = None
    date_released: Optional[str] = None
    version_statement: Optional[VersionStatement] = None
    aliases: Optional[List[Alias]] = None
    alternate_identifiers: Optional[List[AlternateIdentifier]] = None
    languages: Optional[List[Language]] = None
    measurement_unit: Optional[str] = None
    dimensions: Optional[List[Dimension]] = None
    release_calendar: Optional[str] = None
    periodicity: Optional[str] = None
    base_period: Optional[str] = None
    definition_short: Optional[str] = None
    definition_long: Optional[str] = None
    definition_references: Optional[List[Reference]] = None
    statistical_concept: Optional[str] = None
    statistical_concept_references: Optional[List[Reference]] = None
    concepts: Optional[List[Concept]] = None
    data_collection: Optional[DataCollection] = None
    methodology: Optional[str] = None
    methodology_references: Optional[List[Reference]] = None
    derivation: Optional[str] = None
    derivation_references: Optional[List[Reference]] = None
    imputation: Optional[str] = None
    imputation_references: Optional[List[Reference]] = None
    adjustments: Optional[List[str]] = None
    missing: Optional[str] = None
    validation_rules: Optional[List[str]] = None
    quality_checks: Optional[str] = None
    quality_note: Optional[str] = None
    sources_discrepancies: Optional[str] = None
    series_break: Optional[str] = None
    limitation: Optional[str] = None
    themes: Optional[List[Vocabulary]] = None
    topics: Optional[List[Vocabulary]] = None
    disciplines: Optional[List[Vocabulary]] = None
    relevance: Optional[str] = None
    mandate: Optional[Mandate] = None
    time_periods: Optional[List[TimePeriod]] = None
    ref_country: Optional[List[RefCountry]] = None
    geographic_units: Optional[List[GeographicUnit]] = None
    bbox: Optional[List[BoundingBox]] = None
    aggregation_method: Optional[str] = None
    aggregation_method_references: Optional[List[Reference]] = None
    disaggregation: Optional[str] = None
    license: Optional[List[Reference]] = None
    confidentiality: Optional[str] = None
    confidentiality_status: Optional[str] = None
    confidentiality_note: Optional[str] = None
    citation_requirement: Optional[str] = None
    links: Optional[List[Link]] = None
    api_documentation: Optional[List[ApiDocumentation]] = None
    sources: Optional[List[Source]] = None
    sources_note: Optional[str] = None
    keywords: Optional[List[Keyword]] = None
    acronyms: Optional[List[Acronym]] = None
    errata: Optional[List[Erratum]] = None
    acknowledgements: Optional[List[Acknowledgement]] = None
    acknowledgement_statement: Optional[str] = None
    disclaimer: Optional[str] = None
    notes: Optional[List[Note]] = None
    related_indicators: Optional[List[RelatedIndicator]] = None
    compliance: Optional[List[Compliance]] = None
    framework: Optional[List[Framework]] = None
    series_groups: Optional[List[SeriesGroup]] = None
    contacts: Optional[List[Contact]] = None


class Creator(SchemaBaseModel):
    name: str
    nameType: Optional[str] = Field(None, pattern=r"^(Personal|Organizational)$")
    givenName: Optional[str] = None
    familyName: Optional[str] = None


class Title(SchemaBaseModel):
    title: str
    titleType: Optional[str] = Field(None, pattern=r"^(AlternativeTitle|Subtitle|TranslatedTitle|Other)$")
    lang: Optional[str] = None


class ResourceType(SchemaBaseModel):
    resourceType: str
    resourceTypeGeneral: Optional[str] = Field(
        None,
        pattern=r"^(Audiovisual|Collection|DataPaper|Dataset|Event|Image|InteractiveResource|Model|PhysicalObject|Service|Software|Sound|Text|Workflow|Other)$",
    )


class Datacite(SchemaBaseModel):
    doi: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    creators: Optional[List[Creator]] = None
    titles: Optional[List[Title]] = None
    publisher: Optional[str] = None
    publicationYear: Optional[str] = None
    types: Optional[
        ResourceType
    ] = None  # the name suggests this should be an array but that's not what the documentation says
    url: Optional[AnyUrl] = None
    language: Optional[str] = None


class OriginDescription(SchemaBaseModel):
    harvest_date: Optional[str] = None
    altered: Optional[bool] = None
    base_url: Optional[str] = None
    identifier: Optional[str] = None
    date_stamp: Optional[str] = None
    metadata_namespace: Optional[str] = None


class Provenance(SchemaBaseModel):
    origin_description: OriginDescription


class Tag(SchemaBaseModel):
    tag: Optional[str] = None
    tag_group: Optional[str] = None


class TimeSeriesMetadataSchema(SchemaBaseModel):
    idno: str
    metadata_information: Optional[MetadataInformation] = None
    series_description: SeriesDescription
    datacite: Optional[Datacite] = None
    provenance: Optional[List[Provenance]] = None
    tags: Optional[List[Tag]] = None
    additional: Optional[dict] = None
