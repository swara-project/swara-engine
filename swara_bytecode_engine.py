import re
import os
from copy import deepcopy
from enum import Enum, auto

class Opcode(Enum):
    # Variables y Memoria
    SET = auto()
    UPDATE = auto()
    
    # Listas
    LIST_APPEND = auto()
    LIST_POP = auto()
    LIST_SIZE = auto()
    LIST_GET_INDEX = auto()
    LIST_SET_INDEX = auto()
    
    # Control de Flujo
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    
    # Input / Output
    PRINT = auto()
    ASK = auto()
    SEND_PETITION = auto()
    
    # Funciones y Rutas
    CALL_FUNC = auto()
    RETURN = auto()


class _GiveException(Exception):
    def __init__(self, value):
        self.value = value

class swaraBytecodeEngine:
    def __init__(self):
        self.variables = {}
        self.current_layer = None
        self.current_file = ""
        self.links = {"fncs": [], "dtta": [], "lgca": [], "sttr": []}
        self.forms = {}
        self.functions = {}
        self.history = []
        self.input_handler = input
        self.output_handler = print
        self.routes = {}
        self.entry_point = None
        self.error_handler = None
        self.compiled_link_files = set()
        self.allowed_scope = None
        self.route_transitions = {}

    def error(self, error_type, message, line_num="?"):
        error_msg = f"[{error_type}] Line {line_num} in '{self.current_file}':\n-> {message}"
        raise Exception(error_msg)

    def load_file(self, path):
        if not str(path).endswith(".swara"):
            return None
        self.current_file = path
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _normalize_behavior(self, behavior_str):
        if not behavior_str:
            return None
        token = behavior_str.strip().lower()
        token = token.replace("-", "").replace(" ", "")
        mapping = {
            "immutable": "immutable",
            "inmutable": "immutable",
            "tipoa": "immutable",
            "a": "immutable",
            "mutable": "mutable",
            "tipob": "mutable",
            "b": "mutable",
            "derived": "derived",
            "derivado": "derived",
            "derivada": "derived",
            "computed": "computed",
            "computado": "computed"
        }
        return mapping.get(token)

    def _parse_form_field_line(self, line):
        match = re.match(r"^(\w+)\s*:\s*(\w+)(.*)$", line)
        if not match:
            return None
        name, type_name, extras = match.groups()
        extras = extras.strip()
        behavior = None
        derived_from = None
        if extras:
            computed_match = re.search(r"behavior\s+(?:computed|computado)\s*\((.*?)\)", extras, re.IGNORECASE)
            if computed_match:
                behavior = "computed"
                derived_from = computed_match.group(1).strip()
            else:
                behavior_match = re.search(r"behavior\s+(?:tipo\s+)?(\w+)", extras, re.IGNORECASE)
                if behavior_match:
                    normalized = self._normalize_behavior(behavior_match.group(1))
                    if normalized:
                        behavior = normalized
                derived_match = re.search(r"(?:derived\s+from|from)\s+([a-zA-Z0-9_,\s]+)", extras, re.IGNORECASE)
                if derived_match:
                    derived_from = derived_match.group(1).strip()
                    if not behavior:
                        behavior = "derived"
        if not behavior:
            behavior = "mutable"
        return {"name": name, "type": type_name, "behavior": behavior, "derived_from": derived_from}

    def _enforce_scope(self, var_name, line_num):
        if self.allowed_scope is not None:
            clean_name = str(var_name).replace("dtta.", "").replace("lgca.", "")
            if clean_name not in self.allowed_scope:
                self.error("SCOPE ERROR", f"State Mapping Block: Variable '{clean_name}' is encapsulated and cannot be accessed inside this route.", line_num)

    def _get_field_metadata(self, var_name):
        if "." in var_name:
            form_name, field_name = var_name.split(".", 1)
            form = self.forms.get(form_name)
            if form:
                field_meta = form["fields"].get(field_name)
                if field_meta:
                    return field_meta
        for form in self.forms.values():
            field_meta = form["fields"].get(var_name)
            if field_meta:
                return field_meta
        return None

    def _enforce_mutability_and_warn(self, var_name, behavior, derived_from, line_num, system_update=False, expression=None, is_init=False):
        existing = self.variables.get(var_name)
        if existing and existing.get("behavior") == "immutable":
            self.error("IMMUTABLE ERROR", f"Variable '{var_name}' is immutable and cannot be modified.", line_num)
        behavior = behavior or "mutable"
        
        if behavior == "computed" and not system_update and not is_init:
            if not expression:
                self.error("COMPOSITION ERROR", f"Computed variable '{var_name}' requires its exact components ({derived_from}). You must provide an operation using them.", line_num)
            
            sources = [s.strip() for s in str(derived_from).split(',')]
            missing = []
            for s in sources:
                if not re.search(rf'\b{re.escape(s)}\b', str(expression)):
                    missing.append(s)
            
            if missing:
                self.error("COMPOSITION ERROR", f"Computed variable '{var_name}' requires all its defined components. Missing in expression: {', '.join(missing)}. Required spaces to fill: ({derived_from}).", line_num)

        elif behavior == "derived" and not system_update and not is_init:
            is_valid_recalc = False
            if expression and derived_from:
                sources = [s.strip() for s in str(derived_from).split(',')]
                # Es válido si al menos una de las fuentes de origen se utiliza en la expresión matemática/asignación
                if any(re.search(rf'\b{re.escape(s)}\b', str(expression)) for s in sources):
                    is_valid_recalc = True
                    
            if not is_valid_recalc:
                source_desc = f"'{derived_from}'" if derived_from else "an upstream source"
                self.output_handler(f"[DERIVED WARNING] Line {line_num} - Arbitrary manual change to derived '{var_name}'. Missing sources ({source_desc}) in the update operation.")

    def _register_variable(self, var_name, value, v_type, line_num, system_update=False, expression=None):
        is_init = var_name not in self.variables
        clean_var_name = var_name.replace("dtta.", "").replace("lgca.", "")
        
        if is_init and self.allowed_scope is not None:
            self.allowed_scope.add(clean_var_name)
        else:
            self._enforce_scope(var_name, line_num)

        field_meta = self._get_field_metadata(var_name)
        behavior = "mutable"
        derived_from = None
        expected_type = None
        if field_meta:
            expected_type = field_meta.get("type")
            behavior = field_meta.get("behavior", "mutable")
            derived_from = field_meta.get("derived_from")
        if expected_type and expected_type != v_type:
            self.error("TYPE ERROR", f"Field '{var_name}' expects type '{expected_type}' but got '{v_type}'.", line_num)
        
        expr_to_check = expression if expression is not None else str(value)
        
        # Inferencia de orígenes para datos Derived si no se definieron explícitamente en el dtta
        if is_init and behavior == "derived" and not derived_from and expression:
            words = set(re.findall(r'[a-zA-Z_]\w*', str(expression)))
            inferred = [w for w in words if w in self.variables and w != var_name]
            if inferred:
                derived_from = ", ".join(inferred)
                
        self._enforce_mutability_and_warn(var_name, behavior, derived_from, line_num, system_update, expr_to_check, is_init)
        self.variables[var_name] = {"value": value, "type": v_type, "behavior": behavior, "derived_from": derived_from}

    def validate_passport(self, code):
        passport_regex = r"declare\s+([\w\.]+)\s+ass\s+(sttr|lgca|fncs|dtta)"
        passport_matches = list(re.finditer(passport_regex, code, re.IGNORECASE))
        if not passport_matches:
            raise Exception("[LAYER ARCHITECTURE ERROR] Invalid Passport format.")
        match = passport_matches[0]
        self.current_file = match.group(1).strip()
        self.current_layer = match.group(2).strip().lower()
        
        # Validar el uso de 'delimiter' y que la capa coincida con el passport
        delimiter_regex = r"delimiter\s+(sttr|lgca|fncs|dtta)\s+(\w+)\s*\{([\s\S]*)\}"
        delimiter_match = re.search(delimiter_regex, code, re.IGNORECASE)
        if not delimiter_match:
            raise Exception("[LAYER ARCHITECTURE ERROR] Missing or invalid 'delimiter' block. Expected 'delimiter <layer> <name> { ... }'.")
            
        block_layer = delimiter_match.group(1).lower()
        if block_layer != self.current_layer:
            raise Exception(f"[LAYER ARCHITECTURE ERROR] Layer mismatch. File declared as '{self.current_layer}' but delimiter specifies '{block_layer}'.")
            
        # Extraemos el contenido de todo el programa (ignorando todo hasta el inicio pero preservando 'link from')
        # Para que los links externos (link from ...) funcionen, extraemos solo su bloque para las instrucciones a analizar, 
        # PERO incluimos los 'link from' explícitamente ya que suelen ir afuera del delimiter.
        links = "\n".join(re.findall(r"link\s+from\s+.*?;?", code[:delimiter_match.start()]))
        block_content = delimiter_match.group(3)
        
        return links + "\n" + block_content

    def get_instructions(self, content):
        clean_content = re.sub(r"\/\/.*", "", content)
        raw_lines = clean_content.split("\n")
        instructions = []
        for line_num, raw_line in enumerate(raw_lines, 1):
            line = raw_line.strip()
            if not line: continue
            if line.endswith("{") or line == "}" or line == "};":
                instructions.append((line.replace("};", "}"), line_num))
                continue
            if not line.endswith(";"):
                if not any(kw in line for kw in ["if", "else", "loop", "crte", "form", "switch", "case", "default"]):
                    pass # Evitamos error estricto de sintaxis aquí para simplificar
            instructions.append((line.rstrip(";").strip(), line_num))
        return instructions

    # ─────────────────────────────────────────────
    # COMPILER: String -> Bytecode
    # ─────────────────────────────────────────────
    def compile(self, instructions):
        bytecode = []
        i = 0
        while i < len(instructions):
            line, line_num = instructions[i]
            
            # SET var = val -> type
            if line.startswith("set "):
                if "call function" in line:
                    match = re.search(r"set\s+(\w+)\s*=\s*call function\s+(\w+)\[(.*)\]\s*->\s*(\w+)", line)
                    if match:
                        var_name = match.group(1)
                        func_name = match.group(2)
                        args = [arg.strip() for arg in match.group(3).split(",") if arg.strip()]
                        ret_type = match.group(4)
                        # We push args to operand stack or keep them in instruction
                        bytecode.append((Opcode.CALL_FUNC, var_name, func_name, args, ret_type, line_num))
                elif "ask" in line:
                    match = re.search(r'set\s+(\w+)\s*=\s*ask\s*\["(.*)"\]\s*->\s*(\w+)', line)
                    if match:
                        bytecode.append((Opcode.ASK, match.group(1), match.group(2), match.group(3).strip(), line_num))
                else:
                    match = re.search(r"set\s+(\w+)\s*=\s*(.*)\s*->\s*(\w+)", line)
                    if match:
                        var_name, value, v_type = match.groups()
                        val_clean = value.strip().replace('"', "")
                        list_match = re.match(r"^(\w+)\[(\d+)\]$", val_clean)
                        if list_match:
                            lst_name, idx_str = list_match.groups()
                            bytecode.append((Opcode.LIST_GET_INDEX, var_name, lst_name, int(idx_str), v_type.strip(), line_num))
                        else:
                            bytecode.append((Opcode.SET, var_name, value.strip(), v_type.strip(), line_num))
                i += 1
                
            # PRINT
            elif line.startswith("console.print"):
                match = re.search(r"console\.print\[(.*)\]", line)
                if match:
                    bytecode.append((Opcode.PRINT, match.group(1), line_num))
                i += 1
                
            # UPDATE var = val
            elif line.startswith("update ") and not line.startswith("update.list"):
                match = re.search(r"update\s+([\w\[\]]+)\s*=\s*(.*)", line)
                if match:
                    var_name, expression = match.groups()
                    list_match = re.match(r"^(\w+)\[(\d+)\]$", var_name.strip())
                    if list_match:
                        lst_name, idx_str = list_match.groups()
                        bytecode.append((Opcode.LIST_SET_INDEX, lst_name, int(idx_str), expression.strip(), line_num))
                    else:
                        bytecode.append((Opcode.UPDATE, var_name.strip(), expression.strip(), line_num))
                i += 1

            # UPDATE LISTS
            elif line.startswith("update.list"):
                match = re.search(r"update\.list\[\s*(\w+)\s*,\s*(.*)\s*\]", line)
                if match: bytecode.append((Opcode.LIST_APPEND, match.group(1), match.group(2).strip(), line_num))
                i += 1
            elif line.startswith("pull.list"):
                match = re.search(r"pull\.list\[\s*(\w+)\s*,\s*(\w+)\s*\]", line)
                if match: bytecode.append((Opcode.LIST_POP, match.group(1), match.group(2).strip(), line_num))
                i += 1
            elif line.startswith("size.list"):
                match = re.search(r"size\.list\[\s*(\w+)\s*,\s*(\w+)\s*\]", line)
                if match: bytecode.append((Opcode.LIST_SIZE, match.group(1), match.group(2).strip(), line_num))
                i += 1

            # IF / ELSE IF / ELSE
            elif line.startswith("if"):
                jumps_to_end = []
                
                cond_match = re.search(r"\[(.*?)\]", line)
                cond = cond_match.group(1) if cond_match else "no"
                cond_idx = len(bytecode)
                bytecode.append((Opcode.JUMP_IF_FALSE, cond, -1, line_num))
                
                body_inst, end_i = self._collect_block(instructions, i)
                bytecode.extend(self.compile(body_inst))
                
                jumps_to_end.append(len(bytecode))
                bytecode.append((Opcode.JUMP, -1, line_num))
                
                bytecode[cond_idx] = (Opcode.JUMP_IF_FALSE, cond, len(bytecode), line_num)
                i = end_i + 1
                
                while i < len(instructions):
                    next_line, next_ln = instructions[i]
                    if next_line.startswith("else if"):
                        cond_match = re.search(r"\[(.*?)\]", next_line)
                        cond = cond_match.group(1) if cond_match else "no"
                        cond_idx = len(bytecode)
                        bytecode.append((Opcode.JUMP_IF_FALSE, cond, -1, next_ln))
                        
                        body_inst, end_i = self._collect_block(instructions, i)
                        bytecode.extend(self.compile(body_inst))
                        
                        jumps_to_end.append(len(bytecode))
                        bytecode.append((Opcode.JUMP, -1, next_ln))
                        
                        bytecode[cond_idx] = (Opcode.JUMP_IF_FALSE, cond, len(bytecode), next_ln)
                        i = end_i + 1
                    elif next_line.startswith("else"):
                        body_inst, end_i = self._collect_block(instructions, i)
                        bytecode.extend(self.compile(body_inst))
                        i = end_i + 1
                        break
                    else:
                        break
                        
                for j_idx in jumps_to_end:
                    bytecode[j_idx] = (Opcode.JUMP, len(bytecode), bytecode[j_idx][-1])
                continue

            # LOOP
            elif line.startswith("loop"):
                loop_header = re.search(r"loop\s*\[(.*);(.*);(.*)\]", line)
                init, cond, update = [g.strip() for g in loop_header.groups()]
                
                # 1. Compilamos init (set)
                match_init = re.search(r"set\s+(\w+)\s*=\s*(.*)\s*->\s*(\w+)", init)
                if match_init:
                    bytecode.append((Opcode.SET, match_init.group(1), match_init.group(2), match_init.group(3), line_num))
                
                start_index = len(bytecode) # A donde saltamos en cada iteracion
                
                # 2. Instruction condicional. El destino lo llenaremos despues
                cond_idx = len(bytecode)
                bytecode.append((Opcode.JUMP_IF_FALSE, cond, -1, line_num))
                
                # Obtenemos body y lo compilamos
                body_inst, end_i = self._collect_block(instructions, i)
                body_bytecode = self.compile(body_inst)
                bytecode.extend(body_bytecode)
                
                # 3. Compilamos update
                match_upd = re.search(r"update\s+(\w+)\s*=\s*(.*)", update)
                if match_upd:
                    bytecode.append((Opcode.UPDATE, match_upd.group(1), match_upd.group(2), line_num))
                    
                # 4. Jump de regreso al inicio
                bytecode.append((Opcode.JUMP, start_index, line_num))
                
                # 5. Patch del jump_if_false con el final real
                bytecode[cond_idx] = (Opcode.JUMP_IF_FALSE, cond, len(bytecode), line_num)
                
                i = end_i + 1
                
            # SWITCH / CASE
            elif line.startswith("switch"):
                match = re.search(r"switch\s*\[(.*?)\]", line)
                switch_var = match.group(1).strip() if match else ""
                
                body_inst, end_i = self._collect_block(instructions, i)
                jumps_to_end = []
                
                idx = 0
                while idx < len(body_inst):
                    curr_line, curr_ln = body_inst[idx]
                    if curr_line.startswith("case"):
                        c_match = re.search(r"case\s*\[(.*?)\]", curr_line)
                        c_val = c_match.group(1).strip() if c_match else ""
                        if c_val.isdigit(): cond = f"{switch_var} == {c_val}"
                        else: cond = f"{switch_var} == '{c_val.replace('\"', '')}'"
                        
                        cond_idx = len(bytecode)
                        bytecode.append((Opcode.JUMP_IF_FALSE, cond, -1, curr_ln))
                        
                        case_body, case_end_idx = self._collect_block(body_inst, idx)
                        bytecode.extend(self.compile(case_body))
                        
                        jumps_to_end.append(len(bytecode))
                        bytecode.append((Opcode.JUMP, -1, curr_ln))
                        
                        bytecode[cond_idx] = (Opcode.JUMP_IF_FALSE, cond, len(bytecode), curr_ln)
                        idx = case_end_idx + 1
                    elif curr_line.startswith("default"):
                        def_body, def_end_idx = self._collect_block(body_inst, idx)
                        bytecode.extend(self.compile(def_body))
                        idx = def_end_idx + 1
                    else:
                        idx += 1
                        
                for j_idx in jumps_to_end:
                    bytecode[j_idx] = (Opcode.JUMP, len(bytecode), bytecode[j_idx][-1])
                
                i = end_i + 1
                continue
                
            # FUNCIONES
            elif line.startswith("crte function"):
                match = re.search(r"crte function\s+(\w+)\s*\[(.*?)\]\s*\{", line)
                if match:
                    func_name = match.group(1)
                    params = [p.strip() for p in match.group(2).split(",") if p.strip()]
                    body_inst, end_i = self._collect_block(instructions, i)
                    self.functions[func_name] = {
                        "params": params,
                        "bytecode": self.compile(body_inst)
                    }
                    i = end_i + 1
                    continue
            elif "call function" in line:
                assign_match = re.search(r"set\s+(\w+)\s*=\s*call function\s+(\w+)\[(.*)\]\s*->\s*(\w+)", line)
                if assign_match:
                    var_name, func_name, args_str, ret_type = assign_match.groups()
                    args_list = [a.strip() for a in args_str.split(",") if a.strip()]
                    bytecode.append((Opcode.CALL_FUNC, var_name, func_name, args_list, ret_type, line_num))
                else:
                    direct_match = re.search(r"call function\s+(\w+)\[(.*)\]\s*->\s*(\w+)", line)
                    if direct_match:
                        func_name, args_str, ret_type = direct_match.groups()
                        args_list = [a.strip() for a in args_str.split(",") if a.strip()]
                        discard_var = f"_discard_{line_num}"
                        bytecode.append((Opcode.CALL_FUNC, discard_var, func_name, args_list, ret_type, line_num))
                i += 1
            elif line.startswith("give"):
                match = re.search(r"give\s*\[(.*?)\]", line)
                val = match.group(1).strip() if match else ""
                bytecode.append((Opcode.RETURN, val, line_num))
                i += 1

            # FORMS
            elif line.startswith("form"):
                match = re.search(r"form\s+(\w+)(?:\s+refer\s+(\w+))?\s*\{", line)
                if match:
                    form_name, refer_name = match.groups()
                    inherited_fields = {}
                    if refer_name and refer_name in self.forms:
                        inherited_fields = deepcopy(self.forms[refer_name]["fields"])
                    self.forms[form_name] = {"fields": inherited_fields, "inherits": refer_name}
            
                    body_inst, end_i = self._collect_block(instructions, i)
                    for prop_line, p_ln in body_inst:
                        field_info = self._parse_form_field_line(prop_line.strip())
                        if field_info:
                            self.forms[form_name]["fields"][field_info["name"]] = {
                                "type": field_info["type"],
                                "behavior": field_info["behavior"],
                                "derived_from": field_info["derived_from"],
                                "form": form_name
                            }
                    i = end_i + 1
                    continue

            # LOGIC RUTAS/LINKS (Pasivos)
            elif line.startswith("link from") or line.startswith("entry_point") or line.startswith("error_handler"):
                if line.startswith("link from"):
                    match = re.search(r"link from\s+(sttr|lgca|fncs|dtta)\s*->\s*([\w\.]+)", line)
                    if match:
                        layer, filename = match.groups()
                        self.links[layer].append(filename)
                        # Pre-Caché: Cargar y compilar en tiempo de compilación (Global Scope para forms/fncs)
                        file_key = os.path.normcase(os.path.abspath(filename))
                        if file_key not in self.compiled_link_files:
                            self.compiled_link_files.add(file_key)
                            code = self.load_file(filename)
                            if code:
                                linked_content = self.validate_passport(code)
                                linked_insts = self.get_instructions(linked_content)
                                self.compile(linked_insts)
                elif line.startswith("entry_point"):
                    m = re.search(r"entry_point\s*->\s*([\w\.]+)", line)
                    if m: self.entry_point = m.group(1)
                elif line.startswith("error_handler"):
                    m = re.search(r"error_handler\s*->\s*([\w\.]+)", line)
                    if m: self.error_handler = m.group(1)
                i += 1

            # SEND.PETITION
            elif line.startswith("send.petition"):
                match = re.search(r"send\.petition\[(.*?)\]", line)
                if match: bytecode.append((Opcode.SEND_PETITION, match.group(1).strip(), line_num))
                i += 1

            # RUTAS ACTIVAS
            elif line.startswith("route"):
                if "->" in line:
                    has_block = "{" in line
                    match = re.search(r"route\s+(\w+)\s*->\s*(\w+)(?:\s+when\s+\[(.*?)\])?", line)
                    if match:
                        origin_route = match.group(1)
                        target_route = match.group(2)
                        condition = match.group(3)
                        
                        if origin_route not in self.route_transitions:
                            self.route_transitions[origin_route] = []
                            
                        injected = []
                        if has_block:
                            body_inst, end_i = self._collect_block(instructions, i)
                            for b_line, b_ln in body_inst:
                                if b_line.startswith("inject"):
                                    inj_match = re.search(r"inject\s*\[(.*?)\]", b_line)
                                    if inj_match:
                                        raw_content = inj_match.group(1).strip()
                                        if raw_content:
                                            raw_vars = raw_content.split(",")
                                            injected.extend([v.strip().replace("dtta.", "").replace("lgca.", "") for v in raw_vars])
                            i = end_i + 1
                        else:
                            i += 1
                            
                        self.route_transitions[origin_route].append({
                            "target": target_route,
                            "condition": condition,
                            "injected": injected if injected else None,
                            "line_num": line_num
                        })
                        continue
                elif "{" in line:
                    match = re.search(r"route\s+(\w+)\s*\{", line)
                    if match:
                        route_name = match.group(1)
                        body_inst, end_i = self._collect_block(instructions, i)
                        self.routes[route_name] = self.compile(body_inst)
                        i = end_i + 1
                        continue
                else: 
                    i += 1
                
            else:
                # Ignoramos cosas no implementadas en el demo
                i += 1
                
        return bytecode

    def _collect_block(self, instructions, start_i):
        i = start_i
        while i < len(instructions) and "{" not in instructions[i][0]: i += 1
        body, depth = [], 1
        i += 1
        while i < len(instructions) and depth > 0:
            line, ln = instructions[i]
            if "{" in line: depth += 1
            if line == "}":
                depth -= 1
                if depth == 0: break
            if depth > 0: body.append((line, ln))
            i += 1
        return body, i

    # ─────────────────────────────────────────────
    # EVAL CONDITIONS (Mantenemos eval por ahora)
    # ─────────────────────────────────────────────
    def evaluate_condition(self, condition, line_num="?"):
        processed_cond = condition.replace("&&", " and ").replace("||", " or ")
        tokens = processed_cond.split()
        for i, token in enumerate(tokens):
            if token in self.variables:
                self._enforce_scope(token, line_num)
                val = self.variables[token]["value"]
                tokens[i] = str(val) if self.variables[token]["type"] in ["num", "dec", "bin"] else f"'{val}'"
            elif token == "yes": tokens[i] = "True"
            elif token == "no":  tokens[i] = "False"
        try:
            return bool(eval(" ".join(tokens)))
        except:
            return False

    # ─────────────────────────────────────────────
    # VIRTUAL MACHINE EXECUTION
    # ─────────────────────────────────────────────
    def run_vm(self, bytecode, is_function=False):
        pc = 0
        while pc < len(bytecode):
            instruction = bytecode[pc]
            opcode = instruction[0]
            line_num = instruction[-1]

            try:
                if opcode == Opcode.SET:
                    _, var_name, value, v_type, _ = instruction
                    clean_val = value.replace('"', "")
                    if v_type == "num":
                        # Eval para matematicas rapidas
                        expr = clean_val
                        for vn, vd in self.variables.items():
                            if re.search(rf"\b{vn}\b", expr):
                                self._enforce_scope(vn, line_num)
                            expr = re.sub(rf"\b{vn}\b", str(vd["value"]), expr)
                        try: clean_val = int(eval(expr))
                        except: pass
                    elif v_type == "list":
                        if clean_val.startswith("[") and clean_val.endswith("]"):
                            inner = clean_val[1:-1].strip()
                            if not inner: clean_val = []
                            else:
                                items = [x.strip().replace('"', '') for x in inner.split(",")]
                                parsed = []
                                for item in items:
                                    try: parsed.append(int(item))
                                    except: parsed.append(item)
                                clean_val = parsed
                        else: clean_val = []
                    self._register_variable(var_name, clean_val, v_type, line_num, expression=value)
                    pc += 1

                elif opcode == Opcode.UPDATE:
                    _, var_name, expression, _ = instruction
                    expr = expression
                    for vn, vd in self.variables.items():
                        if re.search(rf"\b{vn}\b", expr):
                            self._enforce_scope(vn, line_num)
                        expr = re.sub(rf"\b{vn}\b", str(vd["value"]), expr)
                    try: new_val = eval(expr)
                    except: new_val = expression.replace('"', "")
                    
                    var_type = self.variables.get(var_name, {}).get("type")
                    var_meta = self.variables.get(var_name)
                    if var_meta:
                        behavior = var_meta.get("behavior", "mutable")
                        derived_from = var_meta.get("derived_from")
                    else:
                        field_meta = self._get_field_metadata(var_name)
                        behavior = field_meta.get("behavior", "mutable") if field_meta else "mutable"
                        derived_from = field_meta.get("derived_from") if field_meta else None
                    self._enforce_mutability_and_warn(var_name, behavior, derived_from, line_num, expression=expression, is_init=False)
                    if var_type:
                        type_mismatch = False
                        if var_type == "num" and not isinstance(new_val, int) and type(new_val) is not bool:
                            try: new_val = int(new_val)
                            except ValueError: type_mismatch = True
                        elif var_type == "dec" and not isinstance(new_val, (int, float)) and type(new_val) is not bool:
                            try: new_val = float(new_val)
                            except ValueError: type_mismatch = True
                        elif var_type == "bin" and not isinstance(new_val, bool):
                            if new_val == "yes": new_val = True
                            elif new_val == "no": new_val = False
                            else: type_mismatch = True
                        elif var_type == "txt" and not isinstance(new_val, str):
                            new_val = str(new_val)
                        elif var_type == "list" and not isinstance(new_val, list):
                            type_mismatch = True

                        if type_mismatch:
                            self.error("TYPE ERROR", f"Cannot assign value '{new_val}' to variable '{var_name}' of type '{var_type}'.", line_num)

                    self.variables[var_name]["value"] = new_val
                    pc += 1

                elif opcode == Opcode.PRINT:
                    _, content, _ = instruction
                    if content in self.variables:
                        self._enforce_scope(content, line_num)
                        self.output_handler(self.variables[content]["value"])
                    else:
                        self.output_handler(content.replace('"', ""))
                    pc += 1

                elif opcode == Opcode.JUMP_IF_FALSE:
                    _, cond, target_idx, _ = instruction
                    if not self.evaluate_condition(cond, line_num):
                        pc = target_idx
                    else:
                        pc += 1

                elif opcode == Opcode.ASK:
                    _, var_name, prompt, v_type, _ = instruction
                    user_input = self.input_handler(prompt)
                    if user_input is None: user_input = "0" if v_type == "num" else ""
                    try:
                        if v_type == "num": user_input = int(user_input)
                        elif v_type == "dec": user_input = float(user_input)
                    except ValueError:
                        pass
                    
                    self._register_variable(var_name, user_input, v_type, line_num)
                    pc += 1

                elif opcode == Opcode.LIST_APPEND:
                    _, lst_name, val, _ = instruction
                    clean_val = val.replace('"', "")
                    if clean_val in self.variables: 
                        self._enforce_scope(clean_val, line_num)
                        clean_val = self.variables[clean_val]["value"]
                    else: 
                        try: clean_val = int(clean_val)
                        except: 
                            try: clean_val = float(clean_val)
                            except: pass
                    if lst_name in self.variables and self.variables[lst_name]["type"] == "list":
                        self._enforce_scope(lst_name, line_num)
                        self._enforce_mutability_and_warn(
                            lst_name,
                            self.variables[lst_name].get("behavior", "mutable"),
                            self.variables[lst_name].get("derived_from"),
                            line_num,
                            expression="APPEND " + str(val),
                            is_init=False
                        )
                        self.variables[lst_name]["value"].append(clean_val)
                    pc += 1

                elif opcode == Opcode.LIST_POP:
                    _, lst_name, trg_var, _ = instruction
                    if lst_name in self.variables and self.variables[lst_name]["type"] == "list":
                        self._enforce_scope(lst_name, line_num)
                        lst = self.variables[lst_name]["value"]
                        if lst:
                            self._enforce_mutability_and_warn(
                                lst_name,
                                self.variables[lst_name].get("behavior", "mutable"),
                                self.variables[lst_name].get("derived_from"),
                                line_num,
                                expression="POP",
                                is_init=False
                            )
                            val = lst.pop()
                            vt = "num" if isinstance(val, int) else "dec" if isinstance(val, float) else "bin" if isinstance(val, bool) else "txt"
                            self._register_variable(trg_var, val, vt, line_num)
                    pc += 1

                elif opcode == Opcode.LIST_SIZE:
                    _, lst_name, trg_var, _ = instruction
                    if lst_name in self.variables and self.variables[lst_name]["type"] == "list":
                        self._enforce_scope(lst_name, line_num)
                        self._register_variable(trg_var, len(self.variables[lst_name]["value"]), "num", line_num)
                    pc += 1

                elif opcode == Opcode.LIST_GET_INDEX:
                    _, var_name, lst_name, idx, v_type, _ = instruction
                    if lst_name in self.variables and self.variables[lst_name]["type"] == "list":
                        self._enforce_scope(lst_name, line_num)
                        lst = self.variables[lst_name]["value"]
                        if 0 <= idx < len(lst):
                            found_val = lst[idx]
                            if v_type == "num": found_val = int(found_val)
                            elif v_type == "dec": found_val = float(found_val)
                            elif v_type == "txt": found_val = str(found_val)
                            elif v_type == "bin": found_val = bool(found_val)
                            self._register_variable(var_name, found_val, v_type, line_num)
                        else:
                            self.error("INDEX ERROR", f"Index {idx} out of bounds for list '{lst_name}'.", line_num)
                    else:
                        self.error("REFERENCE ERROR", f"Variable '{lst_name}' is not a list or doesn't exist.", line_num)
                    pc += 1

                elif opcode == Opcode.LIST_SET_INDEX:
                    _, lst_name, idx, expression, _ = instruction
                    expr = expression
                    for vn, vd in self.variables.items():
                        if vd["type"] not in ["list", "empty"]:
                            if re.search(rf"\b{vn}\b", expr):
                                self._enforce_scope(vn, line_num)
                            expr = re.sub(rf"\b{vn}\b", str(vd["value"]), expr)
                    try: new_val = eval(expr)
                    except: new_val = expression.replace('"', "")
                    if lst_name in self.variables and self.variables[lst_name]["type"] == "list":
                        self._enforce_scope(lst_name, line_num)
                        lst = self.variables[lst_name]["value"]
                        if 0 <= idx < len(lst):
                            self._enforce_mutability_and_warn(
                                lst_name,
                                self.variables[lst_name].get("behavior", "mutable"),
                                self.variables[lst_name].get("derived_from"),
                                line_num,
                                expression=expression,
                                is_init=False
                            )
                            lst[idx] = new_val
                        else:
                            self.error("INDEX ERROR", f"Index {idx} out of bounds for list '{lst_name}'.", line_num)
                    else:
                        self.error("REFERENCE ERROR", f"Variable '{lst_name}' is not a list or doesn't exist.", line_num)
                    pc += 1

                elif opcode == Opcode.CALL_FUNC:
                    _, var_name, func_name, args_list, ret_type, _ = instruction
                    
                    if func_name in self.functions:
                        func_data = self.functions[func_name]
                        saved_vars = dict(self.variables) # Backup Scope
                        
                        for param, arg in zip(func_data["params"], args_list):
                            if arg in self.variables: 
                                self._enforce_scope(arg, line_num)
                                self.variables[param] = dict(self.variables[arg])
                            else:
                                try: self.variables[param] = {"value": int(arg), "type": "num"}
                                except: self.variables[param] = {"value": arg.replace('"', ""), "type": "txt"}
                        
                        return_val = self.run_vm(func_data["bytecode"], is_function=True)
                        self.variables = saved_vars # Restore Scope
                        self._register_variable(var_name, return_val, ret_type, line_num)
                    pc += 1

                elif opcode == Opcode.RETURN:
                    _, val, _ = instruction
                    ret_val = val
                    if val in self.variables: 
                        self._enforce_scope(val, line_num)
                        ret_val = self.variables[val]["value"]
                    elif val == "yes": ret_val = True
                    elif val == "no": ret_val = False
                    elif val: ret_val = val.replace('"', "")
                    return ret_val

                elif opcode == Opcode.SEND_PETITION:
                    _, content, _ = instruction
                    if content in self.variables:
                        self._enforce_scope(content, line_num)
                        payload = self.variables[content]["value"]
                    else:
                        payload = content
                    self.output_handler(f"[NETWORK MOCK]: Sending petition -> {payload}")
                    pc += 1


                elif opcode == Opcode.JUMP:
                    _, target_idx, _ = instruction
                    pc = target_idx

                else:
                    pc += 1

            except Exception as e:
                # Si la excepcion ya contiene nuestro formato de error, la relanzamos
                if str(e).startswith("["): 
                    raise
                # Atrapamos cualquier error inesperado de Python (ej eval) y le ponemos la linea
                self.error("RUNTIME ERROR", str(e), line_num)
                
        if is_function: return None

    def start_routing(self):
        if not self.entry_point: return
        current_route = self.entry_point
        self.allowed_scope = None
        while current_route:
            # print(f"\n[ROUTING]: >>> Entering station '{current_route}' >>>")
            if current_route in self.routes:
                body = self.routes[current_route]
            else:
                # Si la ruta no está en routes, intentamos cargarla del archivo linkeado
                code = self.load_file(current_route)
                if not code:
                    # print(f"[SYSTEM WARNING]: Route '{current_route}' logic is not defined.")
                    break
                content = self.validate_passport(code)
                insts = self.get_instructions(content)
                body = self.compile(insts)

            snapshot = deepcopy(self.variables)
            try:
                self.run_vm(body)
                next_route = None
                injected_scope = None
                
                # Evaluamos transiciones usando el estado final de las variables tras ejecutar la ruta actual
                if current_route in self.route_transitions:
                    for transition in self.route_transitions[current_route]:
                        condition = transition["condition"]
                        if not condition or self.evaluate_condition(condition, transition["line_num"]):
                            next_route = transition["target"]
                            if next_route in self.variables:
                                self._enforce_scope(next_route, transition["line_num"])
                                next_route = str(self.variables[next_route]["value"])
                            injected_scope = transition["injected"]
                            break
                            
                if next_route:
                    current_route = next_route
                    if injected_scope is not None:
                        self.allowed_scope = set(injected_scope)
                    else:
                        self.allowed_scope = None
                else:
                    break
            except Exception as e:
                self.variables = snapshot
                if self.error_handler:
                    current_route = self.error_handler
                    self.allowed_scope = None
                else:
                    raise e

    def execute(self, instructions):
        # We perform compilation first
        main_bytecode = self.compile(instructions)
        # We start route loop if there is an entry point
        if self.entry_point:
            self.start_routing()
        else:
            self.run_vm(main_bytecode)

    def run(self, code):
        content = self.validate_passport(code)
        instructions = self.get_instructions(content)
        
        # print("[COMPILER] Translating code to bytecode...")
        self.execute(instructions)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python swara_bytecode_engine.py file.swara")

        sys.exit(1)

    interpreter = swaraBytecodeEngine()
    code = interpreter.load_file(sys.argv[1])
    if code:
        interpreter.run(code)
