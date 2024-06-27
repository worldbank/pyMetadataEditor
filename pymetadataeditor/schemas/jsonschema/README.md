# Source:

Timeseries (accessed 20June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/timeseries-schema.json

Datacite (accessed 20June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/datacite-schema.json

Provenance (accessed 20June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/provenance-schema.json

Survey (AKA Microdata) (accessed 24June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/survey-schema.json

DDI (accessed 24June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/ddi-schema.json

Datafile (accessed 24June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/datafile-schema.json

Variable (accessed 24June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/variable-schema.json

Variable Group (accessed 24June2024): https://metadataeditorqa.worldbank.org/api-documentation/editor/variable-group-schema.json


# todo: 

* Right now running datamodel-codegen with a link to the web definitions of these json schemas doesn't work because of issues with the links inside timeseries-schema.json to the datacite-schema.json and provenance-schema.json schemas. If the versions at the above sources are the "source of truth" then we should use them without having to save copies.

* Update the timeseries.series_description.authoring_entity.abbreviation and series_description.authoring_entity.email to have a type

* Both timeseries and survey metadata have fields for AuthoringEntityItem but they are slightly different. Find out if we can align them. Also for DataCollection, Topic, TimePeriod, Source

* Survey Metadata schema even has two similar but different fields called Contact, can these be aligned?

* We should update the json schemas for URL and URI fields so that they can't be just any string but must be valid URI "uri": {
                                "title": "URI",
                                "description": "URI",
                                "type": "string",
                                "format": "uri"
                            }

* Is there a way to get datamodel-codegen not to create duplicate definitions of entities degined in common_schemas.py?