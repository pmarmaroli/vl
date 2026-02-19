import sys
from pathlib import Path

# Add parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent.parent / 'src'
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from vl.compiler import Compiler

tests = [
    ('x=py:np.array([1,2,3])', 'numpy array'),
    ('df=py:pd.read_csv(data.csv)', 'pandas read_csv'),
    ('F:test|S|O|ret:py:json.loads(i0)', 'json.loads in function'),
    ('result=py:scipy.stats.norm.pdf(0.5)', 'scipy function'),
    ('v:result=py:requests.get(http://api.com).json()', 'chained method calls'),
]

for code, desc in tests:
    print(f'Test: {desc}')
    print(f'VL:   {code}')
    try:
        c = Compiler(code, type_check_enabled=False)
        out = c.compile()
        print(f'PY:   {out.strip()}')
        print('✓ Success\n')
    except Exception as e:
        print(f'✗ Error: {e}\n')
