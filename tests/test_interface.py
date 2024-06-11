from pymetadataeditor.interface import MetadataEditor
import requests
import pytest
import pandas as pd


class MockResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self.json_data = json_data if json_data is not None else {}

    def raise_for_status(self):
        if self.status_code == 403:
            raise requests.exceptions.HTTPError("403 Client Error: Forbidden for url", response=self)
        elif self.status_code != 200:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error")
        
    def json(self):
        return self.json_data

@pytest.mark.parametrize("method", ["get", "post"])
def test_given_request(monkeypatch, method):
    me = MetadataEditor(api_key = 'test')
    if method == 'get':
        func = lambda *args, **kwargs: me._get_request(*args, **kwargs)
    elif method == 'post':
        func = lambda *args, **kwargs: me._post_request(*args, **kwargs, metadata={})
    
    # url is not https
    url = 'http://example.com' 
    with pytest.raises(ValueError):
        func(url)

    # api key raises Access Denied
    url = 'https://example.com'
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=403)
    monkeypatch.setattr(requests, 'request', mock_response)
    with pytest.raises(PermissionError):
        func(url)
    
    # api raises some other http error
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=502)
    monkeypatch.setattr(requests, 'request', mock_response)
    with pytest.raises(Exception):
        func(url)

    # response is good
    def mock_response(*args, **kwargs):
        return MockResponse(status_code=200, json_data={})
    monkeypatch.setattr(requests, 'request', mock_response)
    func(url)


def test_list_collections(monkeypatch):
    collections = {'status': 'success',
                   'projects': [{'id': '1',
                                 'created': '2024-06-11T09:58:14-04:00'},
                                {'id': '2',
                                 'created': '2024-06-11T09:58:14-04:00'}
                                 ],
                  }
    def mock_get(*args, **kwargs):
        return MockResponse(status_code=200, json_data=collections)
    monkeypatch.setattr(requests, 'request', mock_get)

    me = MetadataEditor(api_key='test')
    actual_collections = me.list_collections()
    assert type(actual_collections) == pd.DataFrame
    assert actual_collections.shape == (2, 1)
    assert actual_collections.columns == ['created']

def test__quick_validate_metadata():
    me = MetadataEditor(api_key='test')


    data_is_string = """{"idno": "GB123"}"""
    with pytest.raises(ValueError):
        me._quick_validate_metadata(data_is_string)

    data_misses_idno = {}
    with pytest.raises(ValueError):
        me._quick_validate_metadata(data_misses_idno)


def test_create_timeseries(monkeypatch):
    metadata = {
            "idno": "GB123",
            "series_description": {
                "idno": "string",
                "doi": "string",
                "name": "Gordons Test",
                "display_name": "string"
                }
            }
    def mock_post(*args, **kwargs):
        return MockResponse(status_code=200)
    monkeypatch.setattr(requests, 'request', mock_post)
    me = MetadataEditor(api_key='test')
    me.create_timeseries(metadata=metadata)

