import json
import requests
import frappe
from dataclasses import dataclass

class SandboxUnavailable(frappe.ValidationError):
    pass

@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False

def _get_config():
    url = frappe.conf.get("assessflow_judge0_url")
    if not url:
        raise SandboxUnavailable("Code execution not configured. Set assessflow_judge0_url in site_config.")
    return url.rstrip("/"), frappe.conf.get("assessflow_judge0_key", "")

def _build_source(language, code, func_name, input_data):
    """Wrap candidate code in a test harness."""
    
    if language == "python":
        harness = f"""
import json
{code}

try:
    args = {input_data}
    if isinstance(args, dict): result = {func_name}(**args)
    elif isinstance(args, list): result = {func_name}(*args)
    else: result = {func_name}(args)
    print(json.dumps({{"result": result}}))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
        return harness

    elif language == "javascript":
        harness = f"""
{code}

try {{
    const args = {input_data};
    let result;
    if (Array.isArray(args)) {{
        result = {func_name}(...args);
    }} else {{
        result = {func_name}(args);
    }}
    console.log(JSON.stringify({{ result }}));
}} catch (e) {{
    console.log(JSON.stringify({{ error: e.message }}));
}}
"""
        return harness

    elif language == "html":
        try:
            spec = json.loads(input_data)
            selector = spec.get("selector", "")
            expected_text = spec.get("text", "")
        except Exception:
            selector, expected_text = "", ""
            
        harness = f"""
import json, re
html = {json.dumps(code)}
selector = {json.dumps(selector)}
expected_text = {json.dumps(expected_text)}
try:
    if not selector:
        print(json.dumps({{"error": "No selector provided"}}))
    else:
        tag = re.match(r'^[a-zA-Z0-9]+', selector).group(0)
        regex = re.compile(rf'<{{tag}}[^>]*>(.*?)</{{tag}}>', re.IGNORECASE | re.DOTALL)
        matches = regex.findall(html)
        if not matches:
            print(json.dumps({{"error": f"Element <{{tag}}> not found"}}))
        elif expected_text and not any(expected_text in m for m in matches):
            print(json.dumps({{"error": f"Text '{{expected_text}}' not found"}}))
        else:
            print(json.dumps({{"result": "true"}}))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
        return harness

    raise SandboxUnavailable(f"Unsupported language: {language}")


def run_test_case(language, code, func_name, input_data, expected_output, time_limit=5):
    base_url, api_key = _get_config()
    
    source = _build_source(language, code, func_name, input_data)
    
    piston_lang = "python" if language == "html" else language
    if piston_lang == "javascript": piston_lang = "node"
    
    filename = "main.py" if piston_lang == "python" else "main.js"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    payload = {
        "language": piston_lang,
        "version": "*",
        "files": [{"name": filename, "content": source}],
        "stdin": "",
        "run_timeout": time_limit * 1000
    }

    try:
        r = requests.post(
            f"{base_url}/api/v2/execute",
            json=payload, headers=headers, timeout=time_limit + 10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        raise SandboxUnavailable(f"Runner request failed: {e}")

    run_data = data.get("run", {})
    stdout = run_data.get("stdout", "")
    stderr = run_data.get("stderr", "")
    code_exit = run_data.get("code", 0)

    if run_data.get("signal") == "SIGKILL":
        return RunResult("", "Time Limit Exceeded", -1, True)

    # Parse the JSON result from the harness
    try:
        out = json.loads(stdout.strip())
        if "error" in out:
            return RunResult("", out["error"], 1)
        return RunResult(str(out["result"]), "", 0)
    except Exception:
        # If it's not JSON, it's likely a raw error trace
        return RunResult(stdout.strip(), stderr, 0 if code_exit == 0 else 1)


def grade_coding_question(question, code_payload):
    if not code_payload or not isinstance(code_payload, str):
        return 0, False, "No submission."
    total, awarded, diags = 0.0, 0.0, []
    func_name = question.get("coding_function_name") or "solve"
    for tc in (question.test_cases or []):
        total += float(tc.marks or 0)
        try:
            r = run_test_case(question.coding_language, code_payload, func_name,
                              tc.input_data or "[]", tc.expected_output or "", 5)
        except SandboxUnavailable as e:
            return 0, True, str(e)
        got = r.stdout.strip().strip('"').strip("'")
        exp = (tc.expected_output or "").strip().strip('"').strip("'")
        ok = (not r.timed_out) and (got == exp)
        if ok:
            awarded += float(tc.marks or 0)
        diags.append({"test": tc.description or "Test",
                      "hidden": bool(tc.is_hidden),
                      "passed": ok, "stderr": r.stderr[:500]})
    return awarded, False, json.dumps(diags)


def run_public_tests(question, code):
    if not code or not isinstance(code, str):
        return {"ok": False, "error": "No code submitted."}
    public = [t for t in (question.test_cases or []) if not t.is_hidden]
    if not public:
        return {"ok": False, "error": "No public test cases."}
    results, passed = [], 0
    func_name = question.get("coding_function_name") or "solve"
    for tc in public:
        try:
            r = run_test_case(question.coding_language, code, func_name,
                              tc.input_data or "[]", tc.expected_output or "")
        except SandboxUnavailable as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": f"Runner error: {e}"}
        got = r.stdout.strip().strip('"').strip("'")
        exp = (tc.expected_output or "").strip().strip('"').strip("'")
        ok = (not r.timed_out) and (got == exp)
        if ok:
            passed += 1
        results.append({"id": tc.name, "description": tc.description or "Test",
                        "passed": ok, "expected": exp, "stdout": got,
                        "stderr": r.stderr, "timed_out": r.timed_out})
    return {"ok": True, "tests": results, "summary": {"passed": passed, "total": len(results)}}
