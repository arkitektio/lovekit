"""lovekit must stay importable, and correct, without arkitekt.

arkitekt is an optional integration. Two places may know about it: the integration
module ``lovekit/arkitekt.py``, and ``lovekit/__init__.py``, which imports that module
behind ``try/except ImportError``. Everything else, and above all the executor, is
handed its client instead of importing.
"""

import ast
import subprocess
import sys
from pathlib import Path

import lovekit

PACKAGE = Path(lovekit.__file__).parent
MAY_KNOW_ARKITEKT = {PACKAGE / "arkitekt.py", PACKAGE / "__init__.py"}


def _module_scope_imports(tree: ast.Module) -> list[str]:
    """Names imported where they run at import time: not inside a function body.

    ``if TYPE_CHECKING:`` blocks never run, so they do not count either.
    """
    found: list[str] = []

    def visit(nodes: list[ast.stmt]) -> None:
        for node in nodes:
            if isinstance(node, ast.Import):
                found.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.append(node.module)
            elif isinstance(node, ast.If):
                if "TYPE_CHECKING" not in ast.unparse(node.test):
                    visit(node.body)
                visit(node.orelse)
            elif isinstance(node, (ast.Try, ast.With, ast.ClassDef)):
                for field in ("body", "orelse", "finalbody"):
                    visit(getattr(node, field, []))
                for handler in getattr(node, "handlers", []):
                    visit(handler.body)

    visit(tree.body)
    return found


def test_only_the_integration_module_imports_arkitekt() -> None:
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path in MAY_KNOW_ARKITEKT:
            continue
        imports = _module_scope_imports(ast.parse(path.read_text()))
        if any(name == "arkitekt" or name.startswith("arkitekt.") for name in imports):
            offenders.append(str(path.relative_to(PACKAGE)))

    assert not offenders, (
        f"{offenders} import arkitekt at module scope. lovekit works without arkitekt: "
        "take the client as a reference instead of importing it."
    )


def test_lovekit_imports_and_calls_through_a_client_with_arkitekt_unavailable() -> None:
    """In a fresh interpreter where ``import arkitekt`` fails, as on a bare install."""
    script = (
        "import sys\n"
        "sys.modules['arkitekt'] = None\n"  # makes every `import arkitekt` raise ImportError
        "import asyncio\n"
        "import lovekit\n"
        "from types import SimpleNamespace as NS\n"
        "from lovekit.lovekit import Lovekit\n"
        "class R:\n"
        "    async def aquery(self, document, variables):\n"
        "        return NS(data={'stream': {'id': variables['id'], '__typename': 'Stream'}})\n"
        "client = Lovekit.model_construct(rath=R())\n"
        "assert asyncio.run(client.aget_stream('s-1')).id == 's-1'\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, cwd=PACKAGE.parent
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
