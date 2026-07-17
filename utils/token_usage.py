
def extract_token_usage(result) -> int:
    
    # LangChain usage_metadata (most common for chain.invoke())
    metadata = getattr(result, "usage_metadata", None)
    if metadata and isinstance(metadata, dict):
        total = metadata.get("total_tokens", 0)
        if total:
            return int(total)
        inp = metadata.get("input_tokens", 0)
        out = metadata.get("output_tokens", 0)
        return int(inp) + int(out)

    # LangChain response_metadata (alternative location)
    resp_meta = getattr(result, "response_metadata", None)
    if resp_meta and isinstance(resp_meta, dict):
        token_usage = resp_meta.get("token_usage", {})
        if token_usage and isinstance(token_usage, dict):
            total = token_usage.get("total_tokens", 0)
            if total:
                return int(total)
            inp = token_usage.get("prompt_tokens", 0)
            out = token_usage.get("completion_tokens", 0)
            return int(inp) + int(out)

    # Direct Groq API response (resume builder)
    usage = getattr(result, "usage", None)
    if usage:
        total = getattr(usage, "total_tokens", 0)
        if total:
            return int(total)
        inp = getattr(usage, "prompt_tokens", 0)
        out = getattr(usage, "completion_tokens", 0)
        return int(inp) + int(out)

    return 0
