
# Placeholder runner: adapt to CAT's actual CLI once integrated.
# For now, we mimic a plausible output dict to exercise the pipeline.
def run_cat(params: dict) -> dict:
    # TODO: translate params -> CAT input & call external tool
    # The following mock is only for scaffolding tests.
    return {
        "attacks": {
            "isd-bkz-hybrid": {"rop": 2.3e45, "succ": 0.51},
            "stern": {"rop": 1.1e46, "succ": 0.50}
        },
        "meta": {"model": "CAT-mock-0.1"}
    }
