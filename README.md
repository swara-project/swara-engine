# swara Language Core

Welcome to the internal core implementation of the **swara project**. The core comprises the compiler, runtime environment, and bytecode evaluation engine that power swara's strictly layered architecture (`sttr`, `lgca`, `fncs`, `dtta`).

## 📋 Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [CLI Usage](#cli-usage)
4. [Engine Details & Opcodes](#engine-details--opcodes)
5. [Layer Mechanics](#layer-mechanics)

---

## 🏗 Architecture Overview

The swara Language enforces a **strict Separation of Concerns** through file layer declarations (`ass [layer]`). The core engine validates and evaluates these files independently but cooperatively:

- **sttr (Structure):** Defines the backbone of the application. It maps `entry_point`s and handles structural routing (`route`). Contains NO logic.
- **lgca (Logic):** The brain. Responsible for execution flow (conditionals, loops), variable manipulation, and I/O operations.
- **fncs (Functions):** Reusable blocks of logic. Creates decoupled operations invoked by `lgca`.
- **dtta (Data):** Establishes forms, database molds, structural relationships (`refer`), and behavior-driven mutations (mutable, immutable, computed, derived).

Failure to respect layer boundaries instantly raises a `Layer Architecture Error` within the engine.

---

## 🧠 Core Components

The Core module processes and executes swara projects. It consists of three primary modules:

### 1. `swara_cli.py` (Command-Line Interface)
The entry point for executing scripts. It provides the terminal commands needed to trigger the runtime execution. It accepts paths either to an entire workspace (directory) or directly to a single `.swara` file.

### 2. `swara_runtime.py` (Runtime Environment)
The `swaraRuntime` wrapper prepares the execution context. 
- It attempts to find the application's `entry_point` inside any `.swara` file declared as `ass sttr`.
- Fallbacks to looking for a base `ass lgca` logic file if no structural map is found.
- Instances the engine, handles I/O attachments, and loads the target execution buffer.

### 3. `swara_bytecode_engine.py` (Engine & Virtual Machine)
The core evaluator (`swaraBytecodeEngine`). It handles:
- **Lexical/State Management:** Keeps track of standard execution states, loaded links, history, and active routes.
- **Form Mutability Enforcement:** Enforces swara's deep mutability schemas (`immutable`, `mutable`, `derived`, `computed`) at runtime.
- **Control Flow:** Computes opcodes like `JUMP`, `JUMP_IF_FALSE`, `CALL_FUNC`.
- **Memory Maps:** Maintains dictionaries for localized variables (`num`, `dec`, `txt`, `bin`, `list`, `empty`), data models (`forms`), and registered functions.

---

## 🚀 CLI Usage

You can run the engine directly from your terminal using Python.

### Run a Workspace
```bash
python core/swara_cli.py run .
# OR simply provide the path to your project folder
python core/swara_cli.py run /path/to/project
```

### Run a Specific File
```bash
python core/swara_cli.py run script.swara
```

### Check Version
```bash
python core/swara_cli.py version
```

---

## ⚙️ Engine Details & Opcodes

The `swaraBytecodeEngine` translates operations into internal Opcodes for systematic evaluation.

### Memory & Variable Constraints
Variables are initiated via `set` and transformed via `update`. Data types (`num`, `dec`, `txt`, `bin`, `list`, `empty`) are strictly evaluated for assignments.

- **Data Tracking / Scope Enforcement:** Variables created or scoped within a specific route block are encapsulated.
- **Form Behaviors**: The engine parses specific syntax rules for fields dynamically:
    - `computed`: Requires exact component expressions to be filled.
    - `derived`: Allows updates but validates operation history upstream.
    - `immutable`: Raises `IMMUTABLE ERROR` upon mutation attempt.
    - `mutable`: Standard behavior.

### Opcodes
The internal virtual machine processes the following opcodes (as defined in `Opcode(Enum)`):
- **Variables**: `SET`, `UPDATE`
- **Lists**: `LIST_APPEND`, `LIST_POP`, `LIST_SIZE`, `LIST_GET_INDEX`, `LIST_SET_INDEX`
- **Control Flow**: `JUMP`, `JUMP_IF_FALSE`
- **I/O**: `PRINT`, `ASK`, `SEND_PETITION`
- **Execution**: `CALL_FUNC`, `RETURN`, `ROUTE_TRANSITION`, `NOOP`

---

## 🧩 Layer Mechanics

### Dependencies
Connections between layers are established using the keyword `link`. When the engine hits `link from [layer] -> [filename].swara;`, the runtime fetches the file, compiles its structures, and appends them to its respective internal lists (`self.links`), effectively building the dependency tree mapped strictly by layer origin before runtime logic gets engaged.

### Form Definitions
Handled internally by `_parse_form_field_line(self, line)`. The Engine extracts not only standard definitions (`name`, `type`) but validates data traits via regular expressions analyzing `behavior`, enabling an incredibly fine-grained reactive data model layer.
