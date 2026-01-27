"""MCP Server exposing DocGemma medical tools.

This module provides an MCP (Model Context Protocol) server that exposes
medical tools for use by agentic AI systems. The server can be run
standalone or integrated into a larger application.

Usage:
    # Run as standalone MCP server (stdio transport)
    python -m docgemma.tools.server

    # Or import and run programmatically
    from docgemma.tools.server import mcp_server
    mcp_server.run()
"""

from __future__ import annotations

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .clinical_trials import find_clinical_trials
from .drug_interactions import check_drug_interactions
from .drug_safety import check_drug_safety
from .medical_literature import search_medical_literature
from .schemas import (
    ClinicalTrialsInput,
    DrugInteractionsInput,
    DrugSafetyInput,
    MedicalLiteratureInput,
    PatientRecordsInput,
)

# Create MCP server instance
mcp_server = Server("docgemma-tools")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available medical tools.

    Returns:
        List of Tool definitions with JSON schemas for the LLM.
    """
    return [
        Tool(
            name="check_drug_safety",
            description=(
                "Check for FDA boxed warnings (black box warnings) on a medication. "
                "These are the most serious warnings indicating life-threatening risks. "
                "Use this before prescribing any medication to verify safety."
            ),
            inputSchema=DrugSafetyInput.model_json_schema(),
        ),
        Tool(
            name="search_medical_literature",
            description=(
                "Search PubMed for relevant medical articles and retrieve abstracts. "
                "Use this to find evidence-based information, treatment guidelines, "
                "or recent research on medical conditions. Returns top 3 results by default."
            ),
            inputSchema=MedicalLiteratureInput.model_json_schema(),
        ),
        Tool(
            name="check_drug_interactions",
            description=(
                "Check for drug-drug interactions between multiple medications. "
                "Queries FDA drug labels to find interaction warnings. "
                "ALWAYS use this before adding new medications to a patient's regimen."
            ),
            inputSchema=DrugInteractionsInput.model_json_schema(),
        ),
        Tool(
            name="find_clinical_trials",
            description=(
                "Search for ACTIVELY RECRUITING clinical trials on ClinicalTrials.gov. "
                "Use this to help patients find experimental treatments when standard "
                "care has failed. Returns up to 3 trials with contact info and locations. "
                "Only shows trials currently enrolling patients."
            ),
            inputSchema=ClinicalTrialsInput.model_json_schema(),
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool by name with the given arguments.

    Args:
        name: The tool name to execute.
        arguments: Tool arguments matching the input schema.

    Returns:
        List containing a single TextContent with the JSON result.

    Raises:
        ValueError: If the tool name is unknown.
    """
    if name == "check_drug_safety":
        input_data = DrugSafetyInput(**arguments)
        result = await check_drug_safety(input_data)

    elif name == "search_medical_literature":
        input_data = MedicalLiteratureInput(**arguments)
        result = await search_medical_literature(input_data)

    elif name == "check_drug_interactions":
        input_data = DrugInteractionsInput(**arguments)
        result = await check_drug_interactions(input_data)

    elif name == "find_clinical_trials":
        input_data = ClinicalTrialsInput(**arguments)
        result = await find_clinical_trials(input_data)

    else:
        raise ValueError(f"Unknown tool: {name}")

    # Return result as JSON text
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for running the MCP server."""
    import asyncio

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
