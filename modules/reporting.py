def format_comparison(comparison: dict) -> str:
    if not comparison or "error" in comparison:
        return ""

    lines = [
        "=" * 60,
        f"HISTORICAL COMPARISON - vs {comparison['vs']}",
        "=" * 60,
    ]

    for metric in comparison["metrics"]:
        if metric["delta"] is not None:
            lines.append(
                f"  {metric['label']:<25} {str(metric['prev']):<12} "
                f"-> {str(metric['curr']):<12} ({metric['note']})"
            )
        else:
            lines.append(
                f"  {metric['label']:<25} {str(metric['prev']):<12} "
                f"-> {str(metric['curr']):<12} [{metric['note']}]"
            )

    return "\n".join(lines)
