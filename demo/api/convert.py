import sys
import os
import json
from http.server import BaseHTTPRequestHandler

CHARS_PER_TOKEN = 2.58

def estimate_tokens(text):
    """Estimate token count from character count"""
    return int(len(text) / CHARS_PER_TOKEN + 0.5)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            self._handle_request()
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.send_error_response(500, f'Internal server error: {str(e)}\nFull traceback:\n{tb}')
    
    def _handle_request(self):
        try:
            # Add VL compiler to path inside the handler
            api_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(api_dir)
            vl_compiler_path = os.path.join(project_root, 'vl-compiler', 'src')
            
            if vl_compiler_path not in sys.path:
                sys.path.insert(0, vl_compiler_path)
            
            # Import inside try block
            try:
                # Import ast_nodes first to ensure all classes are available
                import vl.ast_nodes
                from vl.py_to_vl import convert_python_to_vl
            except ImportError as e:
                import traceback
                tb = traceback.format_exc()
                self.send_error_response(500, f'Import error: {str(e)}\nTraceback:\n{tb}\nPath: {vl_compiler_path}')
                return
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            python_code = data.get('python_code', '').strip()
            
            if not python_code:
                self.send_error_response(400, 'No Python code provided')
                return
            
            # Step 1: Convert Python to VL
            try:
                vl_code = convert_python_to_vl(python_code)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.send_error_response(400, f'Python to VL conversion failed: {str(e)}\nTraceback:\n{tb}')
                return
            
            # Step 2: Convert VL back to Python
            try:
                from vl.lexer import Lexer
                from vl.parser import Parser
                from vl.codegen.python import PythonCodeGenerator
                
                lexer = Lexer(vl_code)
                tokens = lexer.tokenize()
                parser = Parser(tokens)
                ast = parser.parse()
                generator = PythonCodeGenerator(ast)
                roundtrip_python = generator.generate()
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                error_detail = f'VL to Python conversion failed: {str(e)}\nTraceback:\n{tb}\n\nGenerated VL code:\n{vl_code}'
                self.send_error_response(400, error_detail)
                return
            
            # Calculate token counts
            original_tokens = estimate_tokens(python_code)
            vl_tokens = estimate_tokens(vl_code)
            roundtrip_tokens = estimate_tokens(roundtrip_python)
            
            # Send success response
            response = {
                'success': True,
                'vl_code': vl_code,
                'roundtrip_python': roundtrip_python,
                'original_tokens': original_tokens,
                'vl_tokens': vl_tokens,
                'roundtrip_tokens': roundtrip_tokens,
                'savings': original_tokens - vl_tokens,
                'savings_percent': round((original_tokens - vl_tokens) / original_tokens * 100, 1) if original_tokens > 0 else 0
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_error_response(500, f'Internal server error: {str(e)}')
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def send_error_response(self, code, message):
        """Send error response as JSON"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_response = {'success': False, 'error': message}
        self.wfile.write(json.dumps(error_response).encode('utf-8'))
