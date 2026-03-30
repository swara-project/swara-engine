# The Swara Project Core

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

- **sttr (Structure):** Defines the backbone of the application. It employs a centralized Orchestration Pattern for routing (instead of direct jumping), maps `entry_point`s, handles structural routing (`route`), and defines fallbacks via `error_handler -> [route];`. Contains NO logic.
- **lgca (Logic):** The brain. Responsible for execution flow (conditionals, loops), variable manipulation, and I/O operations.
- **fncs (Functions):** Reusable blocks of logic. Creates decoupled operations invoked by `lgca`.
- **dtta (Data):** Establishes forms, database molds, structural relationships (`refer`), and behavior-driven mutations (mutable, immutable, computed, derived).

Failure to respect layer boundaries instantly raises a `Layer Architecture Error` within the engine.

---

## 🧠 Core Components

The Core module processes and executes swara projects. It consists of four primary modules:

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
- **Control Flow:** Computes centralized route orchestrations and calls (`CALL_FUNC`). Direct jumping opcodes have been replaced entirely by the centralized Orchestration Pattern.
- **Memory Maps:** Maintains dictionaries for localized variables (`num`, `dec`, `txt`, `bin`, `list`, `empty`), data models (`forms`), and registered functions.

### 4. `swara_http_lib.py` (Native Network Subsystem)
Modular library handling external microservices interoperability decoupled from the main engine (`send.petition`). Unifies external interactions under Swara context standards:
- **Idempotency checks** mapped automatically against `sys.tx_id`.
- Factory **Exponential Backoff** automatic retries on 500s limits.
- On-the-fly **Data Mapping** natively matching inbound JSON structures cleanly to `dtta` layer forms seamlessly returning `sys.last_response`.

### 5. `swara_time_lib.py` (Native Time Guardian)
Built-in internal library decoupled from the engine handling time manipulations and executions, providing route diagnostics.
- Includes precision sleep timeouts via `std.time.delay`.
- Complete date extraction, format standardizations (`strftime` standardizing), and differential parsing for chronometers natively.

### 6. `swara_math_lib.py` (Native Precision Calculus)
Built-in module designed primarily to address finance and IoT analytics without forcing standard global variables into unsafe states.
- Currency safety handling (`std.math.round`).
- Analytics extraction directly off variables or dynamic list structures (`std.math.sum`, `std.math.mean`, `std.math.min`, `std.math.max`, `std.math.abs`).

### 7. `swara_crypto_lib.py` (Native Bouncer Subsystem)
Zero-dependency symmetrical encryption core designed to give developers immediate security over networking payloads. Evaluates standard robust cryptographic patterns completely separated from the VM.
- Data hashing directly onto single state values via `std.crypto.hash` with standard SHA-256. 
- Shared-key HMAC-SHA-256 Payload signing ensuring microservice routing trust mechanisms with `std.crypto.sign`.
- Full stream cipher symmetrical text base64 obfuscation (`std.crypto.encrypt`, `std.crypto.decrypt`).

### 8. `swara_json_lib.py` (Universal Translator)
Bridging Swara cleanly to external payloads seamlessly with robust validations attached explicitly to the strict native Forms defined in the `dtta` Layer. Throws explicit `SCHEMA ERROR` events, acting completely as an impenetrable boundary for garbage logic attempting to disrupt local VM behaviors.
- Validate, structure bindings, and generate safe localized JSON translation structures locally utilizing `std.json.parse` or cleanly parsing standard variables utilizing `std.json.serialize`.

### 9. swara_mask_lib.py (Data Obfuscation)
Provides standard data masking functions to protect sensitive information (PII, PCI-DSS, etc.) before writing it to logs, console output, or checkpoint files (.swchk). This is crucial for maintaining security when using persist.
- Credit cards (std.mask.credit_card).
- Emails (std.mask.email).
- Complete hiding (std.mask.hidden).

### 10. `swara_db_lib.py` (Database Interoperability)
Built-in native support for SQLite databases, bridging standard relational database functionality directly into Swara's memory maps.
- Tunnel and interface direct persistent connections dynamically onto state variables (`open.db`).
- Execute transparently robust queries, where results automatically parse down into standard arrays / variables safely within the logic scope boundaries (`exec.db`).

### 11. `swara_server_lib.py` (API Listener)
Allows Swara to run as a backend server and listen to HTTP requests natively.
- Boots up gracefully acting as a web server mapped to an execution `route` using `listen.api`.
- Native RESTful returns and responses using explicit codes directly managed from within logic flows via `reply.api`.

### 12. `swara_html_lib.py` (Interface Translator Engine)
Bridging Swara cleanly to User Interfaces. Directly interpolate variables from memory or parsed data forms straight into robust HTML architectures seamlessly off `.swara` variables using `fill.html`.


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

### State & Immutability Contracts
Variables are initiated via `set` and transformed via `update`. Data types (`num`, `dec`, `txt`, `bin`, `list`, `empty`) are strictly evaluated for assignments.

- **Data Tracking / Boundary Enforcement:** Variables created or scoped within a specific route block are thoroughly encapsulated according to our *Shared-Nothing Architecture*. The engine utilizes a Shadow Copy state projection and restricts state transfer strictly to `inject` declarations. If un-injected entities are queried, a `BOUNDARY ERROR` is raised, acting as a logical firewall to prevent side effect spillovers.
- **Engine Journaling & Rehydration (Immortal Checkpoints):** Swara seamlessly handles fault-tolerant state persistence. Use the `persist;` keyword within `route` mapping keys to safely snapshot the orchestrated state to `.swchk` files. The engine guarantees *"Exactly Once"* interactions via the intrinsically provided `sys.tx_id`. Upon an unpredicted hardware or service loss, rebooting the VM automatically rehydrates variable dictionaries and picks up execution at the exact pre-saved route border.
- **Concurrency Support (Fork & Join / Reconcilation):** Branch routing can be performed concurrently using `fork -> [target1], [target2] escape [emergency_route]`. Each branch inherently receives an independent clone of the snapshot, making parallel processing intrinsically thread-safe by bypassing variable mutability entirely. States merge back using `inject_back` commands explicit to each route mapping (`fork -> [ruta_a inject_back saldo], [ruta_b inject_back logs]`). Violating this selectively isolated return scheme generates a boundary exception. If any child thread encounters a critical error, the Orchestrator initiates a Collective Panic Management sequence, bypassing synchronization and safely escaping to the fallback route.
- **Form Behaviors**: The engine parses specific syntax rules for fields dynamically:
    - `computed`: Requires exact component expressions to be filled.
    - `derived`: Allows updates but validates operation history upstream.
    - `immutable`: Raises `IMMUTABLE ERROR` upon mutation attempt.
    - `mutable`: Standard behavior.

### Opcodes
The internal virtual machine processes the following opcodes (as defined in `Opcode(Enum)`):
- **Variables**: `SET`, `UPDATE`
- **Lists**: `LIST_APPEND`, `LIST_POP`, `LIST_SIZE`, `LIST_GET_INDEX`, `LIST_SET_INDEX`
- **Control Flow**: `ROUTE_TRANSITION`, `ORCHESTRATE` (legacy jumping opcodes have been deprecated)
- **I/O & DB**: `PRINT`, `ASK`, `SEND_PETITION`, `OPEN_DB`, `EXEC_DB`, `LISTEN_API`, `REPLY_API`, `FILL_HTML`
- **Execution**: `CALL_FUNC`, `RETURN`, `ROUTE_TRANSITION`, `NOOP`

---

## 🧩 Layer Mechanics

### Dependencies
Connections between layers are established using the keyword `link`. When the engine hits `link from [layer] -> [filename].swara;`, the runtime fetches the file, compiles its structures, and appends them to its respective internal lists (`self.links`), effectively building the dependency tree mapped strictly by layer origin before runtime logic gets engaged.

### Form Definitions
Handled internally by `_parse_form_field_line(self, line)`. The Engine extracts not only standard definitions (`name`, `type`) but validates data traits via regular expressions analyzing `behavior`, enabling an incredibly fine-grained reactive data model layer.
