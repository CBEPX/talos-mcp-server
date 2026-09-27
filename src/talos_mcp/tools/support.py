"""Private support bundle creation with explicit encryption selection."""

import json
import shutil
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import Field, model_validator

from talos_mcp.core.client import TalosExecutionError
from talos_mcp.tools.base import TalosTool
from talos_mcp.tools.cluster import NodeSchema


class SupportSchema(NodeSchema):
    """Support bundle options without implicit encryption policy."""

    encryption: Literal["siderolabs", "recipients", "none"]
    recipients: list[str] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def recipients_match_mode(self) -> "SupportSchema":
        """Require explicit recipients and reject ignored keys."""
        if (self.encryption == "recipients") != bool(self.recipients):
            raise ValueError("recipients required only for recipients encryption")
        if any(not key or key.startswith("-") or "\x00" in key for key in self.recipients):
            raise ValueError("invalid recipient")
        return self


class SupportTool(TalosTool):
    """Create a support bundle under the private artifact root."""

    name = "talos_support"
    description = (
        "Generate a private support bundle; select siderolabs, recipients, "
        "or none encryption explicitly."
    )
    args_schema = SupportSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = SupportSchema(**arguments)
        minor = await self.client.client_minor()
        if minor not in {"1.13", "1.14"} or (minor == "1.13" and args.encryption != "none"):
            raise TalosExecutionError("UNSUPPORTED_CAPABILITY")
        directory = self.client.new_artifact_dir()
        path = directory / "support.zip"
        cmd = ["support", "--output", str(path), "-n", args.node]
        if minor == "1.14":
            if args.encryption == "none":
                cmd.append("--no-encryption")
            elif args.encryption == "recipients":
                cmd.append("--encryption-no-default-recipients")
                for recipient in args.recipients:
                    cmd.extend(["--encryption-recipients", recipient])
        try:
            await self.client.execute_talosctl(cmd, operation=self.name)
            return [TextContent(type="text", text=json.dumps(self.client.artifact_metadata(path)))]
        except BaseException:
            shutil.rmtree(directory)
            raise
