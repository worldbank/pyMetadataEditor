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
    with pytest.raises(ValueError) as e:
        validate_metadata(metadata_is_empty, TimeSeriesMetadataSchema)
    assert str(e.value) == "\nmissing: idno field required\nmissing: series_description field required"

    idno_is_wrong_type = {"idno": 17, "series_description": {"idno": "18", "name": "test"}}
    with pytest.raises(ValueError) as e:
        validate_metadata(idno_is_wrong_type, TimeSeriesMetadataSchema)
    assert str(e.value) == "\nstring_type: idno input should be a valid string"

    minimally_good_metadata = {"idno": "17", "series_description": {"idno": "18", "name": "test"}}
    validate_metadata(minimally_good_metadata, TimeSeriesMetadataSchema)

    should_be_list = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": {"uri": "bad_url"}},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(should_be_list, TimeSeriesMetadataSchema)
    assert str(e.value) == "\nlist_type: series_description.definition_references input should be a valid list"

    bad_uri = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": [{"uri": "bad_url"}]},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(bad_uri, TimeSeriesMetadataSchema)
    assert (
        str(e.value) == "\nurl_parsing: series_description.definition_references.0.uri input should be a valid url, "
        "relative url without a base"
    )

    good_uri = {
        "idno": "17",
        "series_description": {
            "idno": "18",
            "name": "test",
            "definition_references": [{"uri": "http://www.example.com"}],
        },
    }
    validate_metadata(good_uri, TimeSeriesMetadataSchema)
