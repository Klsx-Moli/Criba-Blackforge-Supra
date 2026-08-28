"""Native Model Context Protocol (MCP) JSON-RPC 2.0 Handler for SUPRA Agentic Taskmaster.

Exposes standard MCP tools, resources, and prompts over HTTP JSON-RPC 2.0:
  - Tools: supra_decompose, supra_synthesize, supra_verify, supra_sandbox, supra_quick_run
  - Resources: supra://schema/invariants, supra://state/active-projects
  - Prompts: prompt_taskmaster_challenge, prompt_falsification_audit
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .runner import taskmaster_runner
from .state import state_manager
from .tools import (
    decompose_objective,
    execute_sandbox_action,
    record_checkpoint,
    synthesize_strategy,
    verify_solution,
)

MCP_TOOLS_MANIFEST = [
    {
        "name": "supra_quick_run",
        "description": "Execute the full 5-stage autonomous Taskmaster Golden Path for an objective.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "objective": {"type": "string", "description": "The challenge or problem to solve."},
                "domain": {"type": "string", "default": "general"},
            },
            "required": ["objective"],
        },
    },
    {
        "name": "supra_decompose",
        "description": "Deconstruct an objective into core system invariants and mutable assumptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "objective": {"type": "string"},
                "domain": {"type": "string", "default": "general"},
            },
            "required": ["project_id", "objective"],
        },
    },
    {
        "name": "supra_synthesize",
        "description": "Synthesize multi-paradigm strategy candidates (Conservative, Orthogonal, Disruptive).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "pathways_count": {"type": "integer", "default": 3},
                "allow_disruptive": {"type": "boolean", "default": True},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "supra_verify",
        "description": "Formulate formal empirical falsification hypothesis (H0) and verify invariants.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
            },
            "required": ["project_id"],
        },
    },
    {
        "name": "supra_sandbox",
        "description": "Execute AST-parsed synthetic simulation and fuzzing in the isolated micro-sandbox.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "fuzz_iterations": {"type": "integer", "default": 5},
            },
            "required": ["project_id"],
        },
    },
]

MCP_RESOURCES_MANIFEST = [
    {
        "uri": "supra://schema/invariants",
        "name": "Taskmaster System Invariants Schema",
        "mimeType": "application/json",
        "description": "Standard system invariant definitions and boundaries.",
    },
    {
        "uri": "supra://state/active-projects",
        "name": "Active Taskmaster Projects State",
        "mimeType": "application/json",
        "description": "In-memory snapshot of current project lifecycles.",
    },
]

MCP_PROMPTS_MANIFEST = [
    {
        "name": "prompt_taskmaster_challenge",
        "description": "Deconstruct an engineering challenge into formal invariants and orthogonal pathways.",
        "arguments": [
            {"name": "objective", "description": "Target engineering challenge", "required": True},
        ],
    },
    {
        "name": "prompt_falsification_audit",
        "description": "Audit an AI architecture using Judea Pearl counterfactual invariant testing.",
        "arguments": [
            {"name": "project_id", "description": "Project ID to audit", "required": True},
        ],
    },
]


def handle_mcp_jsonrpc_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Process an MCP JSON-RPC 2.0 request and return a compliant response."""
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if not isinstance(method, str):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32600, "message": "Invalid Request: 'method' must be a string"},
        }

    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "supra-agentic-taskmaster", "version": "1.0.0"},
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": MCP_TOOLS_MANIFEST},
            }

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": MCP_RESOURCES_MANIFEST},
            }

        if method == "resources/read":
            uri = params.get("uri")
            if uri == "supra://schema/invariants":
                content = json.dumps({"invariants": ["System integrity", "Memory boundary containment", "Zero-trust verification"]}, indent=2)
            elif uri == "supra://state/active-projects":
                projects = [p.model_dump() for p in state_manager.list_projects(limit=10)]
                content = json.dumps({"active_count": len(projects), "projects": projects}, indent=2)
            else:
                raise ValueError(f"Unknown resource URI: {uri}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": content}]},
            }

        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"prompts": MCP_PROMPTS_MANIFEST},
            }

        if method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "supra_quick_run":
                posture = taskmaster_runner.run_golden_path(
                    objective=args["objective"],
                    domain=args.get("domain", "general"),
                )
                res = posture.model_dump()
            elif tool_name == "supra_decompose":
                res = decompose_objective(args["project_id"], args["objective"], args.get("domain", "general"))
            elif tool_name == "supra_synthesize":
                res = synthesize_strategy(args["project_id"], args.get("pathways_count", 3), args.get("allow_disruptive", True))
            elif tool_name == "supra_verify":
                res = verify_solution(args["project_id"])
            elif tool_name == "supra_sandbox":
                res = execute_sandbox_action(args["project_id"], fuzz_iterations=args.get("fuzz_iterations", 5))
            else:
                raise ValueError(f"Unknown MCP tool: {tool_name}")

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2, ensure_ascii=False)}],
                },
            }

        raise ValueError(f"Method not found: {method}")

    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": str(exc)},
        }
