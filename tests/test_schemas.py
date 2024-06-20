import pytest
from pydantic import ValidationError

from pymetadataeditor.schemas import SchemaBaseModel, TimeSeriesMetadataSchema
from pymetadataeditor.tools import validate_metadata


def test_SchemaBaseModel():
    class SubClassTest(SchemaBaseModel):
        f1: int
        f2: str

    example = SubClassTest(f1=1, f2="two")

    # can update via assignment like a dictionary
    example["f1"] = -1
    assert example.f1 == -1

    # won't accept undefined values
    with pytest.raises(ValidationError):
        # won't accept undefined in updates...
        example["f3"] = 3

        # nor at instantiation
        SubClassTest(f1=1, f2="two", f3=3)


def test_validate_metadata_TimeSeries():
    metadata_is_empty = {}
    with pytest.raises(ValidationError) as e:
        validate_metadata(metadata_is_empty, TimeSeriesMetadataSchema)
    assert e.value.error_count() == 2
    assert e.value.errors()[0]["loc"][0] == "idno"
    assert e.value.errors()[0]["type"] == "missing"
    assert e.value.errors()[1]["loc"][0] == "series_description"
    assert e.value.errors()[1]["type"] == "missing"

    idno_is_wrong_type = {"idno": 17, "series_description": {"idno": "18", "name": "test"}}
    with pytest.raises(ValueError) as e:
        validate_metadata(idno_is_wrong_type, TimeSeriesMetadataSchema)
    assert e.value.error_count() == 1
    assert e.value.errors()[0]["loc"][0] == "idno"
    assert e.value.errors()[0]["type"] == "string_type"

    minimally_good_metadata = {"idno": "17", "series_description": {"idno": "18", "name": "test"}}
    validate_metadata(minimally_good_metadata, TimeSeriesMetadataSchema)

    should_be_list = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": {"uri": "bad_url"}},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(should_be_list, TimeSeriesMetadataSchema)
    assert e.value.error_count() == 1
    assert e.value.errors()[0]["loc"][0] == "series_description"
    assert e.value.errors()[0]["loc"][1] == "definition_references"
    assert e.value.errors()[0]["type"] == "list_type"

    bad_uri = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": [{"uri": "bad_url"}]},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(bad_uri, TimeSeriesMetadataSchema)
    assert e.value.error_count() == 1
    assert e.value.errors()[0]["loc"][0] == "series_description"
    assert e.value.errors()[0]["loc"][1] == "definition_references"
    assert e.value.errors()[0]["loc"][2] == 0
    assert e.value.errors()[0]["loc"][3] == "uri"
    assert e.value.errors()[0]["type"] == "url_parsing"

    good_uri = {
        "idno": "17",
        "series_description": {
            "idno": "18",
            "name": "test",
            "definition_references": [{"uri": "http://www.example.com"}],
        },
    }
    validate_metadata(good_uri, TimeSeriesMetadataSchema)
