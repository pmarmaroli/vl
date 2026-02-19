import os
import sys
import textwrap

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.compiler import Compiler, TargetLanguage


def _norm(source: str) -> str:
    return textwrap.dedent(source).lstrip('\n')


def test_for_loop_dedent_after_break():
    vl_source = _norm(
        """
        M:demo,function,python
        F:loopTest|I|I|
          v:total=0|
          for:i,range(0,3)|
                        v:total=op:+(total,i)|
                    v:after=op:+(total,1)|
                    ret:after
        """
    )

    generated = Compiler(vl_source, TargetLanguage.PYTHON).compile()

    # The statement after the loop should not be indented inside the loop
    expected_snippet = "    for i in range(0, 3):\n        total = total + i\n    after = total + 1"

    assert expected_snippet in generated
