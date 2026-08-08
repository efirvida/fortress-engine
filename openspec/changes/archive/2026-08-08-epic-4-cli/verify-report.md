```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:80ec0e744ca58eece757678f40f1eef07f8d8b2bd045a540a793012e0f5b89ed
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 7/7
scenarios: 11/11
test_command: pytest tests/test_cli/ -v
test_exit_code: 0
test_output_hash: sha256:80ec0e744ca58eece757678f40f1eef07f8d8b2bd045a540a793012e0f5b89ed
build_command: python -c "import ast; ast.parse(open('src/fortress_engine/cli/main.py').read()); print('BUILD_OK')"
build_exit_code: 0
build_output_hash: sha256:f1442cb880a74e4b1de1d178c5fd94b9f63149191c757d5cd429d653fead95f7
```
