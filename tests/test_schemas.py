import pytest

from pymetadataeditor.schemas import validate_metadata


def test_validate_metadata():
    with pytest.raises(AssertionError):
        validate_metadata({}, "bad_schema")

    data_is_string = """{"idno": "GB123"}"""
    with pytest.raises(ValueError):
        validate_metadata(data_is_string, "TimeSeries")


def test_validate_metadata_TimeSeries():
    metadata_is_empty = {}
    with pytest.raises(ValueError) as e:
        validate_metadata(metadata_is_empty, "TimeSeries")
    assert str(e.value) == "\nmissing: idno field required\nmissing: series_description field required"

    idno_is_wrong_type = {"idno": 17, "series_description": {"idno": "18", "name": "test"}}
    with pytest.raises(ValueError) as e:
        validate_metadata(idno_is_wrong_type, "TimeSeries")
    assert str(e.value) == "\nstring_type: idno input should be a valid string"

    minimally_good_metadata = {"idno": "17", "series_description": {"idno": "18", "name": "test"}}
    validate_metadata(minimally_good_metadata, "TimeSeries")

    should_be_list = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": {"uri": "bad_url"}},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(should_be_list, "TimeSeries")
    assert str(e.value) == "\nlist_type: series_description.definition_references input should be a valid list"

    bad_uri = {
        "idno": "17",
        "series_description": {"idno": "18", "name": "test", "definition_references": [{"uri": "bad_url"}]},
    }
    with pytest.raises(ValueError) as e:
        validate_metadata(bad_uri, "TimeSeries")
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
    validate_metadata(good_uri, "TimeSeries")
