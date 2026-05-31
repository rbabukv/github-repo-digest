"""Categorize PRs by area and flag Intel-relevant changes."""

from .github_client import get_pr_diff

AREA_RULES = {
    "Serving/Runtime": [
        "srt/", "python/sglang/srt/", "server", "router", "scheduler",
        "endpoint", "request", "batch", "decode", "prefill",
    ],
    "Kernels/Backend": [
        "kernel", "backend", "cuda", "triton", "xpu", "cpu",
        "attention", "flash", "gemm", "quantiz",
    ],
    "Model Support": [
        "models/", "model_runner", "model_config", "tokenizer",
        "weight", "loader", "architectures",
    ],
    "Performance": [
        "perf", "optim", "benchmark", "profil", "cache", "memory",
        "throughput", "latency", "speculative",
    ],
    "CI/Infra": [
        ".github/", "ci/", "docker", "Dockerfile", "workflow",
        "setup.py", "pyproject", "requirements",
    ],
    "Docs": [
        "docs/", "README", "CHANGELOG", "tutorial", "example",
    ],
}

INTEL_RELEVANT_KEYWORDS = [
    "xpu", "cpu", "intel", "oneapi", "onednn", "mkl", "ipex",
    "openvino", "gaudi", "habana", "amx", "avx", "vnni",
    "int8", "int4", "fp16", "bf16", "quantiz", "woq",
    "serve", "srt/", "runtime", "scheduler", "router",
    "batch", "decode", "prefill", "speculative",
    "kernel", "backend", "attention", "flash_attn",
    "triton", "gemm", "performance", "throughput", "latency",
    "memory", "cache", "kv_cache", "radix",
    "dp", "tp", "tensor_parallel", "data_parallel", "expert_parallel",
]


def categorize_pr(pr):
    """Assign a category to a PR based on title, labels, and diff file paths."""
    title = pr.get("title", "").lower()
    body = (pr.get("body", "") or "").lower()
    labels = [l.get("name", "").lower() for l in pr.get("labels", [])]

    file_paths = []
    details = pr.get("_details", {})
    if details:
        # Try to get file list from PR details (if available from enrichment)
        pass

    search_text = f"{title} {body} {' '.join(labels)}"

    for area, keywords in AREA_RULES.items():
        for kw in keywords:
            if kw in search_text:
                return area

    return "Other"


def is_intel_relevant(pr):
    """Determine if a PR is relevant to Intel's work on SGLang."""
    title = pr.get("title", "").lower()
    body = (pr.get("body", "") or "").lower()[:2000]
    labels = [l.get("name", "").lower() for l in pr.get("labels", [])]

    search_text = f"{title} {body} {' '.join(labels)}"

    matches = []
    for kw in INTEL_RELEVANT_KEYWORDS:
        if kw in search_text:
            matches.append(kw)

    # Relevant if 2+ keyword matches (avoids false positives from single generic terms)
    return len(matches) >= 2, matches[:5]


def enrich_with_categories(prs):
    """Add category and Intel-relevance flag to each PR."""
    for pr in prs:
        pr["_category"] = categorize_pr(pr)
        relevant, matches = is_intel_relevant(pr)
        pr["_intel_relevant"] = relevant
        pr["_intel_matches"] = matches

    return prs


def group_by_category(prs):
    """Group PRs by category, preserving rank order within each group."""
    groups = {}
    for pr in prs:
        cat = pr.get("_category", "Other")
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(pr)

    # Order categories by priority
    category_order = [
        "Serving/Runtime", "Kernels/Backend", "Performance",
        "Model Support", "CI/Infra", "Docs", "Other",
    ]

    ordered = []
    for cat in category_order:
        if cat in groups:
            ordered.append((cat, groups[cat]))

    # Add any remaining categories not in the predefined order
    for cat, prs_list in groups.items():
        if cat not in category_order:
            ordered.append((cat, prs_list))

    return ordered
