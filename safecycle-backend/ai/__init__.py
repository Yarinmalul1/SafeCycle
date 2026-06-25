"""AI roles for the SafeCycle agent pipeline.

Each module here owns one LLM-backed responsibility:
  - input_parser:      free text -> structured scenario
  - safety_filter:     guardrails against unsafe / out-of-scope requests
  - question_generator: ask for missing essential information
  - answer_phraser:    turn engine decisions into clear, kind user-facing text
  - product_catalog:   knowledge about supported contraceptive products
  - history_manager:   per-user conversation / scenario history
"""
