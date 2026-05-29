from pathlib import Path
from typing import Any

import yaml


DEFAULT_WORKFLOW = Path(__file__).parent.parent / "workflows" / "generic.yaml"


def load_workflow_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a workflow YAML config."""
    config_path = Path(path) if path else DEFAULT_WORKFLOW
    if not config_path.exists():
        raise FileNotFoundError(f"Workflow config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    if not isinstance(config, dict):
        raise ValueError(f"Workflow config must be a mapping: {config_path}")

    config.setdefault("name", config_path.stem)
    config.setdefault("columns", {})
    config.setdefault("analysis", {})
    config.setdefault("validation", {})
    config.setdefault("outputs", {})
    config.setdefault("history", {})

    return config

def load_workflow_for_domain(domain: str) -> dict[str, Any]:
    """Load the workflow config for a detected domain, falling back to generic."""
    workflow_path = DEFAULT_WORKFLOW.parent / f"{domain}.yaml"
    if domain != "generic" and workflow_path.exists():
        return load_workflow_config(workflow_path)
    return load_workflow_config()
