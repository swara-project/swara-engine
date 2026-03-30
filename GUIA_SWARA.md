# Guía Completa de Swara (v1.0)

¡Bienvenido a Swara! Este documento es una guía exhaustiva para aprender paso a paso la sintaxis y las verdaderas capacidades de *Project Swara*, incluyendo todos los componentes interpretados por su motor (Engine) base.

Este proyecto obliga a los desarrolladores a mantener una **separación estricta de responsabilidades** a través de una arquitectura basada en capas (Layers) y enrutamiento aislado (Routing de scopes). Todo funciona de acuerdo a reglas que previenen "spaghetti-code" de raíz.

---

## 🏗️ 1. Arquitectura y Capas (Layers)
En Swara, cada archivo tiene un propósito único. Violar esto lanzará un `Layer Architecture Error`. Todo archivo debe declarar a qué capa pertenece en la primera línea.

1. **sttr (Estructura/Structure):** 
   - Define el ciclo de vida y rutas (`route`).
   - El enrutador central donde configuras el `entry_point`.
   - **No** se permite lógica general aquí (ni `if`, ni declaracion de variables estándar).
2. **lgca (Lógica/Logic):** 
   - Condicionales (`if`, `switch`), variables, I/O, ejecución de funciones.
   - Definicion de bloques de lógica enrutada (`delimiter lgca nombre_ruta { ... }`).
3. **fncs (Funciones/Functions):** 
   - Declaración de funciones reutilizables con `crte function` e invocables con `call function`.
4. **dtta (Datos/Data):** 
   - Definición estricta de estructuras de datos (molds) usando `form`.

### 1.1 Declaración (Pasaporte) y Enlaces
Todo archivo **debe** llevar su "pasaporte" en la primera línea:
```swara
declare main.swara ass lgca
```

Para conectar dependencias entre archivos, se usa la instrucción `link from`:
```swara
link from fncs -> utils.swara;
link from dtta -> types.swara;
```

---

## 🏛️ 2. Bloques y Sintaxis por Capa

El flujo de ejecución en Swara está basado en bloques que abren con la palabra `delimiter` indicando la capa interna a la que pertenece ese bloque.

### 🧩 2.1 Capa de Estructura (`sttr`) - Enrutamiento y Scopes
Swara funciona mediante un Patrón de Orquestación Centralizada para el enrutamiento (Centralized Orchestration Pattern), prohibiendo el clásico "jumping". Dejas una ruta, y el orquestador te transiciona a otra. **IMPORTANTE:** Las variables nacen y mueren de forma aislada en su propia ruta. Si cambias de ruta e intentas usar una variable anterior fallará con un `BOUNDARY ERROR`, a menos que las integres al nuevo viaje usando `inject`, el cual funciona como un Contrato de Inmutabilidad de Frontera. Ninguna ruta puede heredar el desorden de la anterior. Si no declaras tu intención de usar un dato, el motor te protege de ti mismo negando el acceso.

En un archivo `sttr` declaras (mediante el Centralized Orchestration Pattern):
* `entry_point -> ruta_inicial;` : Define dónde arranca la VM.
* `route origen -> destino;` : Redirección obligatoria incondicional.
* `route origen -> destino when [condicion];` : Redirección condicional según la variable final evaluada en la ruta origen.
* `error_handler -> [route];` : Redirige centralmente de forma segura en caso de fallos.
* **`inject [variables]`**: Se declara dentro de la llave de un route. Autoriza la migración de variables usando una arquitectura Shared-Nothing. Sirve como cortafuegos lógico.
* **`persist;`**: Se declara dentro de la llave de un route. Le indica al orquestador que debe convertir el estado actual en un "Checkpoint Inmortal" (journaling). Genera un ID de transacción en `sys.tx_id`. Si el sistema cae, retomará desde esa ruta hidratando la memoria automáticamente.
* **`fork -> [route_1 inject_back var1], [route_2] escape [route_error];`**: (Funcionalidad Concurrente) Permite la ejecución paralela y simultánea compartiendo estados inmutables. Si un hilo falla críticamente, se activa la Gestión de Pánico Colectivo: el Orquestador aborta la reconciliación y te redirige a la ruta definida en `escape`.
* **Declaración de Sub-rutas:** Puedes inicializar bloques con `route nombre { ... }`.

**Ejemplo `enrutador.swara`:**
```swara
declare enrutador.swara ass sttr
link from lgca -> vistas.swara;

delimiter sttr setup {
    entry_point -> home_view;
    
    route home_view -> login_view when [logged_in == no] {
        inject [intentos, dtta.session]
        persist; /* Si el sistema se apaga aquí, al volver a encender continuará en login_view */
    }
}
```

### 🧠 2.2 Capa Lógica (`lgca`)
En estos archivos colocarás los bloques de código que ejecutan las operaciones correspondientes para las rutas que llamaste desde `sttr`.

**Ejemplo `vistas.swara`:**
```swara
declare vistas.swara ass lgca

delimiter lgca home_view {
    set logged_in = no -> bin;
    console.print["Bienvenido! Verificando credenciales..."];
    /* Si esta ruta termina en este punto, el router sttr evalúa 'logged_in == no' para saltar a login_view */
}
```

### 🛠️ 2.3 Capa de Funciones (`fncs`)
Sub-rutinas aisladas que solo habitan en su ambiente. Sólo se llaman en tiempo de ejecución de las lógicas.

**Ejemplo `utils.swara`:**
```swara
declare utils.swara ass fncs

delimiter fncs utilidades {
    crte function calcular_iva [precio, pct] {
        set iva = precio * pct -> dec;
        set total = precio + iva -> dec;
        give [total]; /* Retorna el valor evaluado */
    }
}
```

---

## 🧬 3. Tipos de Datos Primitivos
Los valores base que la máquina virtual de Swara puede administrar:
* `num`: Números enteros (Ej. 10).
* `dec`: Decimales o flotantes (Ej. 3.14).
* `txt`: Cadenas de texto puro (Ej. "Hola").
* `bin`: Booleanos (estrictamente `yes` o `no`).
* `list`: Arreglos / Listas de elementos (Ej. [1, 2, 3]).
* `empty`: Valor nulo o indicador de descarte para funciones huecas.

---

## 💾 4. Variables y Memoria
Las variables se declaran con la palabra `set` apuntando al final `-> tipo` a su valor base. Para mutar una ya declarada se usa `update` a secas. Toda línea finaliza con `;`.

**Declaración:**
```swara
set edad = 25 -> num;
set nombre = "Ana" -> txt;
set conf_ids = [1, 2, 3] -> list;
```

**Modificación (Update):**
```swara
update edad = 26;
```

---

## 🖥️ 5. Entrada, Salida y Red (I/O)
Herramientas activadas transversalmente dentro de Swara (Engine):

**Impresión en consola:**
```swara
console.print["Texto explicito a la terminal"];
console.print[nombre_variable];
```

**Espera de Inputs interactivos:**
```swara
set input_user = ask["Escribe tu respuesta: "] -> txt;
```

**Peticiones de Red e Interfaces (Mocking / Network):** 
Una orden pasiva para generar envíos (ideal para micro-servicios y mock API outputs):
```swara
send.petition["http://api.datos.mock.com/info"];
send.petition[variable_o_payload];
```

---

## 🔀 6. Estructuras de Control (Condicionales)
Exclusivas del bloque lógico que operan sin punto y coma al final de sus llaves de bloque `{ }`.

**If / Else If / Else:**
```swara
if [edad > 18] {
    console.print["Adulto"];
} else if [edad == 18] {
    console.print["Límite de edad"];
} else {
    console.print["Menor"];
}
```

**Selección múltiple (Switch):**
```swara
switch [opcion_elegida] {
    case ["A"] {
        console.print["Elegiste la A"];
    }
    case ["B"] {
        console.print["Elegiste la B"];
    }
    default {
        console.print["Valor alterno predeterminado"];
    }
}
```

---

## 🔁 7. Ciclos (Loops)
Swara usa una estructura predecible de un `loop { }` pasándole sus tres argumentos principales a través de comandos nativos de `set;condición;update`.

```swara
loop [set i = 0 -> num; i < 10; update i = i + 1] {
    console.print[i];
};
```

---

## 📦 8. Operaciones Nativas y Listas
El lenguaje cuenta en su compilador con lectura de arreglos sin necesidad de importar librerías.

**Manejo por índices directos:**
Accede instantáneamente y asigna por posición:
```swara
set el_primero = identificadores[0] -> num;
update identificadores[1] = "Intercambio en idx";
```

**Métodos de manipulación estructural de listas:**
* `update.list[lista, nuevo_valor];` : Realiza un append; suma un valor tras el último índice en la matriz.
* `pull.list[lista, variable_huesped];` : Invoca un `List_Pop` del último elemento dinámicamente y lo graba en `variable_huesped`.
* `size.list[lista, var_medidora];` : Mide el tamaño de toda la lista y lo pasa a una variable pre-definida `var_medidora` (tipo `num`).

---

## ⚡ 9. Invocación de Funciones
En los bloques lógicos invocas lo que vive en los bloques `fncs` siempre llamándolo por su directiva `call function`. 

**Asignando la respuesta de `give` a un receptor local:**
```swara
set total = call function calcular_iva[100, 0.16] -> dec;
```

**Ejecución sin retorno (Drop):**
Llamada al vacío, útil para disparar funciones genéricas que no importan el retorno.
```swara
call function imprimir_sistema["Señal local"] -> empty;
```

---

## 🏛️ 10. Modelado de Datos Avanzado (Forms)
Alojado en el territorio puro de `dtta`. Los modelos `form` te permiten configurar esqueletos y moldes similares a bases de datos relacionales u orientadas a objetos. Tienen capacidad de sub-clase o herencia por intermedio de `refer NombrePadre`.

### 10.1 Behaviors (Reglas de Mutabilidad)
Puedes blindar qué ocurrirá con cada variable posterior a la construcción de un registro, definiendo su regla `behavior`. Si se omite, se asigna `mutable`.
* `mutable`: (Default) Podría cambiar usando condicionales y un `update`.
* `immutable` o `inmutable`: Al crearse se graba en piedra. Si luego intentas pasarle un `update`, saltará `IMMUTABLE ERROR`.
* `derived` / `derived from`: El valor deriva o depende lógicamente de un atributo del mismo formulario y su valor debe emanar históricamente de él (Ej., Historial de acciones en una id).
* `computed` / `computado`: El virtual engine hace la matemática solo usando un argumento extra: `computed(formula)`. No puedes usar `update` acá manualmente. Se auto-calcula de manera reactiva.

### 10.2 Sintaxis Práctica de Forms
```swara
declare mis_modelos.swara ass dtta

delimiter dtta esquemas {
    form EntidadBase {
        id : num behavior inmutable
        creado_en : txt behavior inmutable
    }

    form Usuario refer EntidadBase {
        nombre : txt behavior mutable
        apellido : txt
        nombre_completo : txt behavior computed (nombre + " " + apellido)
        historial : list behavior derived from id
    }
}
```

---

## 📝 11. Operadores Disponibles

| Categoría | Símbolos Permitidos | Propósito |
| -------- | ------- | -------- |
| **Aritméticos** | `+`, `-`, `*`, `/` | Uso matemático y concatenado de strings nativo. |
| **Relacionales**| `>`, `<`, `==`, `!=` | Evaluaciones obligatorias en `if` y condicional del routing `when`. |
| **Lógicos** | `&&` (AND), `||` (OR) | Concatenación booleana múltiple. |

---

## 🚀 Resumen Crítico de Construcción (Cheat Sheet)
1. **Punto y Coma (;):** Absolutamente obligatorio al finalizar rutinas genéricas atómicas (`set`, `update`, `link from`, `update.list`, llamadas directas con array o `loop`).
2. **Llaves ({ }):** No llevan punto y coma final. Engloban un núcleo o contexto (`delimiter sttr`, operaciones de `if/switch / default`, funciones y layers).
3. **Control del State (Variables perdidas):** Tu enrutador limpia las variables entre un `route` y otro para aplicar el Principio de Aislamiento. Todo lo que te importa mantener de un paso a otro lo obligas a fluir en las llaves del envío `inject [mi_var]`.
4. **Respetar Arquitectura:** Intentar colocar sintaxis `set` a nivel raíz o un `if` dentro del enrutador va a lanzar fatalidades instantáneas de `ARCH LAYER`. Cada archivo debe ceñirse a la capacidad de su marca `.swara ass capa`.