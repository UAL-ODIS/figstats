import json
import requests
from requests.exceptions import HTTPError


def issue_request(method, url, headers, data=None, binary=False,
                  params=None):
    """Wrapper for HTTP request

    Parameters
    ----------
    method : str
        HTTP method. One of GET, PUT, POST or DELETE

    url : str
        URL for the request

    headers: dict
        HTTP header information

    data: dict
        Figshare article data

    binary: bool
        Whether data is binary or not

    params: dict
        Additional information for URL GET request

    Returns
    -------
    response_data: dict
        JSON response for the request returned as python dict
    """
    if data is not None and not binary:
        data = json.dumps(data)

    response = requests.request(method, url, headers=headers,
                                data=data, params=params)

    try:
        response.raise_for_status()
        try:
            response_data = json.loads(response.text)
        except ValueError:
            response_data = response.content
    except HTTPError as error:
        print('Caught an HTTPError: {}'.format(error))
        print('Body:\n', response.text)
        raise

    return response_data
