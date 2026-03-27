#!/usr/bin/env python3
import sys, traceback
sys.path.insert(0, 'engine')

modules = [
    ("models",              "sagescan_engine.rules.models",           "SageScanConfig"),
    ("schema",              "sagescan_engine.rules.schema",           "CheckType"),
    ("base",                "sagescan_engine.validators.base",        "BaseValidator"),
    ("implementations",     "sagescan_engine.validators.implementations", "UniqueValidator"),
    ("distribution",        "sagescan_engine.validators.distribution","KSTestValidator"),
    ("registry",            "sagescan_engine.validators.registry",    "registry"),
    ("pipeline",            "sagescan_engine.core.pipeline",          "ValidationPipeline"),
    ("runner",              "sagescan_engine.core.runner",            "run_validation"),
    ("report",              "sagescan_engine.core.report",            "ReportGenerator"),
    ("rule_generator",      "sagescan_engine.llm.rule_generator",     "LLMRuleGenerator"),
    ("explanation_generator","sagescan_engine.llm.explanation_generator","ExplanationGenerator"),
]

errors = []
for label, mod, attr in modules:
    try:
        m = __import__(mod, fromlist=[attr])
        getattr(m, attr)
        print(f"PASS  {label}")
    except Exception as e:
        print(f"FAIL  {label}: {e}")
        traceback.print_exc()
        errors.append(label)

print()
if errors:
    print(f"FAILED modules: {errors}")
    sys.exit(1)
else:
    print("All modules imported successfully.")

