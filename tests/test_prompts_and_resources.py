"""Tests for the ``prompts=`` and ``resources=`` hooks on the server builders.

Before this, ``mk_mcp_server`` only took functions-as-tools, so a server that also
ships MCP prompts or resources had to be assembled half declaratively (tools, via
the builder) and half imperatively (prompts/resources, by reaching past the builder
onto the returned ``FastMCP`` object). These verify the hooks are attached by every
builder, that a single callable normalizes like ``prompts``'s tools-side sibling
does, and that a registered prompt/resource is actually reachable. See
i2mint/py2mcp#10.
"""

import asyncio

from py2mcp import mk_mcp_server, mk_mcp_from_refs, mk_mcp_from_store


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def summarize_request(topic: str) -> str:
    """A prompt asking for a summary."""
    return f"Summarize the latest on {topic}."


def review_request() -> str:
    """A second prompt, to test the list/iterable form."""
    return "Please review the above."


def schema() -> dict:
    """A resource returning a JSON schema."""
    return {"type": "object"}


def test_single_prompt_is_attached():
    server = mk_mcp_server(add, prompts=summarize_request)
    names = {p.name for p in asyncio.run(server.list_prompts())}
    assert names == {"summarize_request"}


def test_list_of_prompts_is_attached():
    server = mk_mcp_server(add, prompts=[summarize_request, review_request])
    names = {p.name for p in asyncio.run(server.list_prompts())}
    assert names == {"summarize_request", "review_request"}


def test_no_prompts_means_no_prompts():
    server = mk_mcp_server(add)
    assert asyncio.run(server.list_prompts()) == []


def test_resources_mapping_is_attached_by_uri():
    server = mk_mcp_server(add, resources={"schema://analysis": schema})
    uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert uris == {"schema://analysis"}


def test_no_resources_means_no_resources():
    server = mk_mcp_server(add)
    assert asyncio.run(server.list_resources()) == []


def test_resource_content_is_reachable():
    server = mk_mcp_server(add, resources={"schema://analysis": schema})
    result = asyncio.run(server.read_resource("schema://analysis"))
    assert result.contents[0].content == '{"type": "object"}'


def test_mk_mcp_from_refs_forwards_prompts_and_resources():
    server = mk_mcp_from_refs(
        ["os.path:basename"],
        prompts=summarize_request,
        resources={"schema://analysis": schema},
    )
    prompt_names = {p.name for p in asyncio.run(server.list_prompts())}
    resource_uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert prompt_names == {"summarize_request"}
    assert resource_uris == {"schema://analysis"}


def test_mk_mcp_from_store_forwards_prompts_and_resources():
    server = mk_mcp_from_store(
        {},
        name="item",
        prompts=summarize_request,
        resources={"schema://analysis": schema},
    )
    prompt_names = {p.name for p in asyncio.run(server.list_prompts())}
    resource_uris = {str(r.uri) for r in asyncio.run(server.list_resources())}
    assert prompt_names == {"summarize_request"}
    assert resource_uris == {"schema://analysis"}
