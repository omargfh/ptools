from __future__ import annotations
from typing import Dict, Optional
import requests

from ptools.lib.llm.command import Command, CommandArgument, CommandSchema

class RequestCommand:
    @staticmethod
    def call(
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        limit: int | None = None
    ):
        try:
            response = requests.request(method=method, url=url, headers=headers)
            return {
                'status_code': response.status_code,
                'content': response.text[:limit] if limit else response.text
            }
        except Exception as e:
            return {'error': str(e)}

def parse_headers(value: str) -> Dict[str, str]:
    """
    Convert a string like "Key1:Value1,Key2:Value2" to a dict
    """
    headers = {}
    for pair in value.split(','):
        if ':' in pair:
            k, v = pair.split(':', 1)
            headers[k.strip()] = v.strip()
    return headers

request_command = Command(
    name="request",
    description="Make an HTTP request.",
    possible_schemas=[
        # Simple URL only
        CommandSchema(arguments=[
            CommandArgument(name="url", required=True),
        ], call=RequestCommand.call),
        # Full request with method and optional headers
        CommandSchema(arguments=[
            CommandArgument(name="url", required=True),
            CommandArgument(name="method", required=False, kind='kwarg'),
            CommandArgument(name="headers", required=False, parser=parse_headers, kind='kwarg'),
            CommandArgument(name="limit", required=False, parser=int, kind='kwarg'),
        ], call=RequestCommand.call),
    ]
)

if __name__ == "__main__":
    # Example 1: Simple GET
    res1 = request_command.wrap({
        'command': 'request',
        'args': [
            'https://example.com'
        ]
    })
    print(res1())

    # Example 2: POST with headers
    res2 = request_command.wrap({
        'command': 'request',
        'args': [
            'https://example.com',
            'POST',
            'Authorization: Bearer xyz,Accept: application/json'
        ]
    })
    print(res2())
