"""
Tiny educational Python interpreter for the public demo.
It does NOT call exec/eval and intentionally supports only a small AST subset.
No imports, file/network access, attributes, classes, function definitions or arbitrary builtins.
"""
import ast
import operator

BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
CMP = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
       ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}

class DemoError(Exception): pass

def run_python_demo(source: str) -> str:
    if len(source) > 20_000:
        raise DemoError("Code quá dài (tối đa 20 KB).")
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as e:
        return f"SyntaxError: {e.msg} (dòng {e.lineno})"
    env = {}
    output = []
    steps = [0]

    def tick():
        steps[0] += 1
        if steps[0] > 2500:
            raise DemoError("Vượt giới hạn 2.500 bước chạy.")

    def value(node):
        tick()
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (str, int, float, bool, type(None))):
                if isinstance(node.value, str) and len(node.value) > 4000:
                    raise DemoError("Chuỗi quá dài.")
                return node.value
            raise DemoError("Kiểu dữ liệu không được hỗ trợ.")
        if isinstance(node, ast.Name):
            if node.id not in env: raise DemoError(f"Biến chưa được khai báo: {node.id}")
            return env[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in BIN:
            a, b = value(node.left), value(node.right)
            if isinstance(node.op, ast.Mult):
                if isinstance(a, (str, list, tuple)) and isinstance(b, int) and len(a) * max(0, b) > 4000:
                    raise DemoError("Kết quả quá lớn.")
                if isinstance(b, (str, list, tuple)) and isinstance(a, int) and len(b) * max(0, a) > 4000:
                    raise DemoError("Kết quả quá lớn.")
            if isinstance(node.op, ast.Pow) and (abs(b) > 8 or abs(a) > 10000):
                raise DemoError("Phép lũy thừa vượt giới hạn.")
            result = BIN[type(node.op)](a, b)
            if isinstance(result, (str, list)) and len(result) > 4000:
                raise DemoError("Kết quả quá lớn.")
            if isinstance(result, (int, float)) and abs(result) > 10**12:
                raise DemoError("Kết quả số vượt giới hạn.")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
            return UNARY[type(node.op)](value(node.operand))
        if isinstance(node, ast.List):
            return [value(x) for x in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(value(x) for x in node.elts)
        if isinstance(node, ast.BoolOp):
            vals = [value(x) for x in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = value(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = value(comp)
                if type(op) not in CMP or not CMP[type(op)](left, right): return False
                left = right
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = [value(a) for a in node.args]
            if node.func.id == "print":
                output.append(" ".join(str(a) for a in args))
                return None
            if node.func.id == "range":
                if not 1 <= len(args) <= 3 or not all(isinstance(x, int) for x in args):
                    raise DemoError("range() chỉ nhận 1-3 số nguyên.")
                r = range(*args)
                if len(r) > 100: raise DemoError("Mỗi vòng lặp tối đa 100 phần tử.")
                return r
            if node.func.id in ("len", "str", "int", "float", "sum", "min", "max"):
                funcs = {"len":len, "str":str, "int":int, "float":float, "sum":sum, "min":min, "max":max}
                return funcs[node.func.id](*args)
            raise DemoError("Hàm này không được hỗ trợ trong demo.")
        raise DemoError(f"Cú pháp không được hỗ trợ: {type(node).__name__}")

    def block(stmts):
        for stmt in stmts:
            tick()
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                env[stmt.targets[0].id] = value(stmt.value)
            elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name) and type(stmt.op) in BIN:
                env[stmt.target.id] = BIN[type(stmt.op)](env[stmt.target.id], value(stmt.value))
            elif isinstance(stmt, ast.Expr):
                value(stmt.value)
            elif isinstance(stmt, ast.If):
                block(stmt.body if value(stmt.test) else stmt.orelse)
            elif isinstance(stmt, ast.For) and isinstance(stmt.target, ast.Name):
                iterable = value(stmt.iter)
                if not isinstance(iterable, range): raise DemoError("for chỉ hỗ trợ range().")
                for item in iterable:
                    env[stmt.target.id] = item
                    block(stmt.body)
                if stmt.orelse: block(stmt.orelse)
            elif isinstance(stmt, ast.Pass):
                pass
            else:
                raise DemoError(f"Câu lệnh không được hỗ trợ: {type(stmt).__name__}")
    try:
        block(tree.body)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return "\n".join(output) if output else "Chạy xong. (Không có output)"
