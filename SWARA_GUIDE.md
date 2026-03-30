# Complete Swara Guide (v1.0)

Welcome to Swara! This document is a comprehensive guide to learning the syntax and true capabilities of *Project Swara* step by step, including all components interpreted by its base Engine.

This project forces developers to maintain a **strict separation of concerns** through a Layer-based architecture and isolated Routing (Scope routing). Everything operates according to rules that prevent "spaghetti-code" at its root.

---

## 🏗️ 1. Architecture & Layers
In Swara, every file has a unique purpose. Violating this will throw a `Layer Architecture Error`. Every file must declare which layer it belongs to on the very first line.

1. **sttr (Structure):** 
   - Defines the lifecycle and routes (`route`).
   - The central router where you configure the `entry_point`.
   - General logic is **not** allowed here (no `if`s, no standard variable declarations).
2. **lgca (Logic):** 
   - Conditionals (`if`, `switch`), variables, I/O, function execution.
   - Definition of routed logic blocks (`delimiter lgca route_name { ... }`).
3. **fncs (Functions):** 
   - Declaration of reusable functions with `crte function` and invocable with `call function`.
4. **dtta (Data):** 
   - Strict definition of data structures (molds) using `form`.

### 1.1 Declaration (Passport) and Links
Every file **must** carry its "passport" on the first line:
```swara
declare main.swara ass lgca
```

To connect dependencies between files, the `link from` instruction is used:
```swara
link from fncs -> utils.swara;
link from dtta -> types.swara;
```

---

## 🏛️ 2. Blocks and Syntax by Layer

The execution flow in Swara is based on blocks that open with the word `delimiter` indicating the internal layer to which that block belongs.

### 🧩 2.1 Structure Layer (`sttr`) - Routing and Scopes
Swara works through a Centralized Orchestration Pattern for routing, strictly forbidding classic jumping/goto behavior. You leave a route, and the orchestrator transitions you to another. **IMPORTANT:** Variables are born and die in isolation within their own route. If you change routes and try to use a previous variable, it will fail with a `BOUNDARY ERROR`, unless you carry them over to the new journey using `inject`, which acts as a Boundary Immutability Contract. No route can inherit the mess of a previous one. If you don't declare your intention to use a piece of data, the engine protects you from yourself by denying access.

In a `sttr` file you declare (via the Centralized Orchestration Pattern):
* `entry_point -> initial_route;` : Defines where the VM starts.
* `route origin -> destination;` : Unconditional mandatory redirection.
* `route origin -> destination when [condition];` : Conditional redirection based on the final variable evaluated in the origin route.
* `error_handler -> [route];` : Safely redirects centrally in the event of failures.
* **`inject [variables]`**: Declared inside a route's curly braces. Authorizes the migration of variables using a Shared-Nothing architecture. Serves as a logical firewall.
* **`use [layer] -> "[file]"`**: Dependency injection. Specifies which file to use for an external layer scoped to the following route. Example: `use fncs -> "mid_utils.swara"`.
* **`persist;`**: Declared inside a route's curly braces. Tells the orchestrator to turn the current state into an "Immortal Checkpoint" (journaling). Generates a transaction ID in `sys.tx_id`. If the system crashes, it will resume from this route hydrating memory automatically.
* **`fork -> [route_1 inject_back var1], [route_2] escape [route_error];`**: (Concurrent Functionality) Allows parallel and simultaneous execution sharing immutable states. If a thread fails critically, Collective Panic Management is activated: the Orchestrator aborts reconciliation and redirects you to the route defined in `escape`.
* **Sub-route declaration:** You can initialize blocks with `route name { ... }`.

**Example `router.swara`:**
```swara
declare router.swara ass sttr
link from lgca -> views.swara;

delimiter sttr setup {
    entry_point -> home_view;
    
    route home_view -> login_view when [logged_in == no] {
        use fncs -> "auth_functions.swara"
        inject [attempts, dtta.session]
        persist; /* If the system shuts down here, it will continue in login_view upon restart */
    }
}
```

### 🧠 2.2 Logic Layer (`lgca`)
In these files, you will place the code blocks that execute the corresponding operations for the routes you called from `sttr`.
Optionally and as a best practice, you should use Interface Contracts through the `expects` keyword.

**Example `views.swara`:**
```swara
declare views.swara ass lgca

delimiter lgca home_view expects [attempts -> num, dtta.session -> str] {
    set logged_in = no -> bin;
    call fncs.verify_credentials[attempts];
    console.print["Welcome! Verifying credentials..."];
    /* If this route ends at this point, the sttr router evaluates 'logged_in == no' to jump to login_view */
}
```

### 🛠️ 2.3 Functions Layer (`fncs`)
Subroutines that execute within the context of the calling route (`lgca`). They can directly read and modify environment variables from the context they were called in without needing to require multiple explicit parameters (avoiding "Prop Drilling"). They are only invoked at logic runtime.

**Example `utils.swara`:**
```swara
declare utils.swara ass fncs

delimiter fncs utilities {
    crte function calculate_tax [price, pct] {
        set tax = price * pct -> dec;
        set total = price + tax -> dec;
        give [total]; /* Returns the evaluated value */
    }
}
```

---

## 🧬 3. Primitive Data Types
The base values the Swara virtual machine can manage:
* `num`: Integers (e.g. 10).
* `dec`: Decimals or floating-point numbers (e.g. 3.14).
* `txt`: Pure text strings (e.g. "Hello").
* `bin`: Booleans (strictly `yes` or `no`).
* `list`: Arrays / Lists of elements (e.g. [1, 2, 3]).
* `empty`: Null value or discard indicator for empty functions.

---

## 💾 4. Variables and Memory
Variables are declared using the word `set` followed by the value and pointing to the base type at the end: `-> type`. To mutate an existing one, `update` is used alone. Every statement ends with `;`.

**Declaration:**
```swara
set age = 25 -> num;
set name = "Ana" -> txt;
set conf_ids = [1, 2, 3] -> list;
```

**Modification (Update):**
```swara
update age = 26;
```

---

## 🖥️ 5. Input, Output and Network (I/O)
Transversally activated tools within the Swara Engine:

**Console printing:**
```swara
console.print["Explicit text to the terminal"];
console.print[variable_name];
```

**Awaiting interactive inputs:**
```swara
set user_input = ask["Type your answer: "] -> txt;
```

**Network and Interface Requests (HTTP / Idempotency):** 
A native command securely connected to our modular HTTP library handling external interoperability. No longer a passive mock, but rather a functional, self-managed requester:
- It automatically injects an `X-Idempotency-Key` header evaluating the `sys.tx_id` global engine variable (to prevent duplicate payments or operations).
- Factory-level status code control:
  - **HTTP 200**: Parses the JSON response gracefully to Swara's native engine mapping, dropping the result inside the `sys.last_response` default variable.
  - **HTTP 400/404**: Instantly throws a crateric native `NETWORK ERROR`.
  - **HTTP >= 500**: The library independently implements a retry system under the hood (*Exponential Backoff*, maximum 3 retries).
- Automatically capable of matching incoming JSON maps straight to `dtta` layer `form` molds, structuring the incoming schemas dynamically.

```swara
send.petition["http://api.mock.data.com/info"];
send.petition[variable_or_payload];
```

**std.time (The Time Guardian):**
Built-in native module crafted for accurately measuring the time offset between workflow routes, auditing timestamps, and effectively running delay blockers safely.
```swara
// Retrieve current exact timestamp (ISO 8601)
set start = call function std.time.now[] -> txt;

// Add a safe blocking script execution delay (e.g., 2.5 seconds)
call function std.time.delay[2.5] -> empty;

// Compare two dates (generates time split result in seconds)
set diff = call function std.time.compare[end_date, start_date] -> num;

// Format native timestamps (using standard strftime format)
set log_date = call function std.time.format[start, "%Y-%m-%d"] -> txt;
```

**std.math (Precision Calculus):**
Ideal for Finance or IoT workflows. Provides rounding schemas, analytic statistical functions, and deep transformations cleanly without corrupting variable scopes:
```swara
// Currency or precision roundings (e.g., 2 decimals)
set rounded_price = call function std.math.round[12.34567, 2] -> dec;

// Absolute value
set absolute = call function std.math.abs[-50] -> num;

// List operations / Metrics
set total = call function std.math.sum[prices_list] -> dec;
set mean_val = call function std.math.mean[temperature_list] -> dec;
set upper = call function std.math.max[measurement_list] -> num;
```

**std.crypto (The Vault):**
The security guardian inside Swara. Perfect for hashing payloads, ensuring secure inter-service communications, and handling state encryption on user variables.
```swara
// Destructive one-way hash transformations (SHA-256)
set checksum_data = call function std.crypto.hash[my_variable] -> txt;

// Sign message integrity employing a secret shared key (HMAC-SHA-256)
set signature = call function std.crypto.sign[message_body, "SECRET_KEY"] -> txt;

// Symmetrical state encryption handling private variables natively
set cyphered = call function std.crypto.encrypt[private_variable, "PASSWORD123"] -> txt;
set decrypted = call function std.crypto.decrypt[cyphered, "PASSWORD123"] -> txt;
```

**std.json (The Universal Translator):**
If Swara is meant to communicate with the world, it needs to handle JSON gracefully without sacrificing strong typing. Converts explicitly to and from data structures (Forms defined in the `dtta` layer).
```swara
// Parse JSON text into a validated Form (Throws a SCHEMA ERROR if there is a missing or extra field in the JSON)
set user = call function std.json.parse[json_string, UserForm] -> UserForm;

// Transform a fully evaluated local Form into a plain JSON string
set output_txt = call function std.json.serialize[user] -> txt;
```


**std.mask (Data Obfuscation):**
Allows hiding or anonymizing sensitive information (Credit Cards, Emails, or plain text) before it gets saved into the persist; checkpoint files, or before logging it into terminal outputs:
`swara
// Mask a credit card (Returns ****-****-****-XXXX)
set card = call function std.mask.credit_card[data.card] -> txt;

// Mask an email address (Returns a***@domain.com)
set email = call function std.mask.email[user.email] -> txt;

// Mask completely sensitive text into asterisks
set hidden = call function std.mask.hidden[pwd] -> txt;
`

**std.limit (Rate Limiting):**
Native library to prevent your API from being saturated or receiving DoS attacks. Stops execution instantly if the IP exceeds the limit.
```swara
// Blocks connections from 'ip' if it exceeds 10 requests in 1 second.
limit.api[ip, 10, 1];
```
---

## 🔀 6. Control Structures (Conditionals)
Exclusive to logic blocks, these operate without a semicolon at the end of their block braces `{ }`.

**If / Else If / Else:**
```swara
if [age > 18] {
    console.print["Adult"];
} else if [age == 18] {
    console.print["Age limit"];
} else {
    console.print["Minor"];
}
```

**Multiple selection (Switch):**
```swara
switch [chosen_option] {
    case ["A"] {
        console.print["You chose A"];
    }
    case ["B"] {
        console.print["You chose B"];
    }
    default {
        console.print["Alternative default value"];
    }
}
```

---

## 🔁 7. Cycles (Loops)
Swara uses a predictable `loop { }` structure by passing its three main arguments through native `set;condition;update` commands.

```swara
loop [set i = 0 -> num; i < 10; update i = i + 1] {
    console.print[i];
};
```

---

## 📦 8. Native Operations and Lists
The language includes array reading in its compiler with no need to import libraries.

**Direct index handling:**
Access instantly and assign by position:
```swara
set the_first = identifiers[0] -> num;
update identifiers[1] = "Swap at idx";
```

**List structural manipulation methods:**
* `update.list[list, new_value];` : Performs an append; adds a value after the last index in the array.
* `pull.list[list, host_variable];` : Invokes a dynamic `List_Pop` of the last element and saves it into `host_variable`.
* `size.list[list, measuring_var];` : Measures the length of the entire list and passes it to an existing `measuring_var` variable (of type `num`).
### Text & List Manipulations (Transformations)
Crucial to process queries returning from inputs (`ask`) or API responses (`send.petition`). In multiple shapes, they allow unrolling and rolling strings organically.

* `split.txt[variable, separator, dest_list];` : Splits text into segments divided by the given separator and injects them as indexes onto a defined `list` element.
* `join.list[list, connector, dest_txt];` : Inverse action. Glues the elements back together placing a string connector achieving a joined `txt` sequence.
* `clean.txt[variable];` : Acts exactly as "trim". Clears trailing and starting blank spaces on your variable re-updating it without manually commanding `update`.
* `find.txt[source, search, result_bin];` : Verifies if a substring in `search` occurs within a `source`. Stores evaluating truth output boolean `yes` or `no` directly sequentially to `result_bin`.

### File System Operations (Disk Management)
Swara incorporates file boundaries using "sandbox" principles. To protect your disks maliciously, reading and writing files is forcibly contained down to an automatically created `/storage` sub-directory near the engine runtime execution folder.

* `write.file["filepath.txt", content];` : Dumps a variable string or explicitly declared raw text generating/overwriting the indicated target (Ex. `records.txt` writes physically on `storage/records.txt`).
* `read.file["filepath.txt", dest_var];` : Engages a disk read operation, finding the target matching inside `/storage` depositing raw string contents inside an existing `txt` `dest_var`.
* `check.file["filepath.txt", bin_var];` : Quietly reviews file existence before crashing your workflow in a standard read, feeding your `bin_var` with logical existence verification result.
---

## ⚡ 9. Function Invocation
Inside logic blocks, you trigger what lives in `fncs` blocks always calling it via the `call function` directive.

**Assigning the return from `give` to a local receiver:**
```swara
set total = call function calculate_tax[100, 0.16] -> dec;
```

**Execution without return (Drop):**
Null call, useful to trigger generic functions where the return value doesn't matter.
```swara
call function print_system["Local signal"] -> empty;
```

---

## 🏛️ 10. Advanced Data Modeling (Forms)
Housed strictly inside the `dtta` territory. The `form` models allow you to configure skeletons and molds similar to relational or object-oriented databases. They hold sub-classing or inheritance capabilities through `refer ParentName`.

### 10.1 Behaviors (Mutability Rules)
You can armor what happens to every variable after the construction of a record by defining its `behavior` rule. If omitted, it defaults to `mutable`.
* `mutable`: (Default) Could change using conditionals and an `update`.
* `immutable` / `inmutable`: Once created, it's set in stone. Attempting to pass an `update` to it later will throw an `IMMUTABLE ERROR`.
* `derived` / `derived from`: The value derives or depends logically on an attribute from the same form, and its value must historically emanate from it (e.g., Action history on an ID).
* `computed` / `computado`: The virtual engine performs the math alone using one extra argument: `computed(formula)`. You cannot manually use `update` here. It calculates itself reactively.

### 10.2 Practical Forms Syntax
```swara
declare my_models.swara ass dtta

delimiter dtta schemas {
    form BaseEntity {
        id : num behavior immutable
        created_at : txt behavior immutable
    }

    form User refer BaseEntity {
        first_name : txt behavior mutable
        last_name : txt
        full_name : txt behavior computed (first_name + " " + last_name)
        history : list behavior derived from id
    }
}
```

---

## 📝 11. Available Operators

| Category | Allowed Symbols | Purpose |
| -------- | ------- | -------- |
| **Arithmetic**| `+`, `-`, `*`, `/` | Mathematical use and native string concatenation. |
| **Relational**| `>`, `<`, `==`, `!=` | Mandatory evaluations in `if` and routing `when` conditionals. |
| **Logical** | `&&` (AND), `||` (OR) | Multiple boolean concatenation. |

---

## 🚀 Critical Build Summary (Cheat Sheet)
1. **Semicolon (;):** Absolutely mandatory at the end of atomic generic routines (`set`, `update`, `link from`, `update.list`, direct calls via array or `loop`).
2. **Curly Braces ({ }):** Do not carry a final semicolon. They encompass a core or context (`delimiter sttr`, `if/switch / default` operations, functions and layers).
3. **State Control (Lost variables):** Your router clears variables between one `route` and the next applying the Isolation Principle. Everything you care about keeping from one step to another must be pushed into the scope using `inject [my_var]`.
4. **Respect Architecture:** Attempting to place a `set` syntax at the root level or an `if` inside the router will instantly trigger fatal `ARCH LAYER` errors. Each file must strictly adhere to the capabilities mandated by its `.swara ass layer` mark.
