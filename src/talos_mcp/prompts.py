"""MCP Prompts implementation for Talos."""

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent

from talos_mcp.core.client import TalosClient


class TalosPrompts:
    """Talos Prompts handler."""

    def __init__(self, client: TalosClient) -> None:
        """Initialize TalosPrompts.

        Args:
            client: TalosClient instance
        """
        self.client = client

    async def list_prompts(self) -> list[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="diagnose_cluster",
                description="Diagnose cluster health and issues",
                arguments=[
                    PromptArgument(
                        name="node",
                        description="Optional specific node IP to focus diagnosis on",
                        required=False,
                    )
                ],
            ),
            Prompt(
                name="audit_review",
                description="Review audit logs",
                arguments=[
                    PromptArgument(
                        name="limit",
                        description="Number of log lines to analyze (default 50)",
                        required=False,
                    )
                ],
            ),
        ]

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> list[PromptMessage]:
        """Get a prompt by name."""
        arguments = arguments or {}

        if name == "diagnose_cluster":
            node = arguments.get("node")
            node_context = f" for node {node}" if node else ""
            return [
                PromptMessage(
                    content=TextContent(
                        type="text",
                        text=f"""Please analyze the Talos cluster status{node_context}.
Run the following checks in order:
1. Check `talos_health` to see overall cluster state.
2. If there are unhealthy nodes, use `talos_service --node <IP>` to list failing services.
3. For any failing service, get logs using `talos_logs`.
4. Check `talos_get_stats` for resource usage.
5. Summarize the findings and recommend fixes.
""",
                    ),
                    role="user",
                )
            ]
        elif name == "audit_review":
            limit = int(arguments.get("limit", "50"))
            return [
                PromptMessage(
                    content=TextContent(
                        type="text",
                        text=f"""Please review the dashboard and audit logs.
1. Run `talos_dashboard` to get a snapshot of current activity.
2. Check `talos_dmesg` (last {limit} lines) for any kernel errors or warnings.
3. Summarize any potential security or stability issues found.
""",
                    ),
                    role="user",
                )
            ]
        else:
            raise ValueError(f"Unknown prompt: {name}")
