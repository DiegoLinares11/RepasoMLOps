# 09 · Docker, Docker Compose y microservicios

🎬 Video: [▶️ en español](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/09-docker-es.mp4) · [▶️ in English](https://github.com/DiegoLinares11/RepasoMLOps/releases/download/videos/09-docker-en.mp4) · [todos los videos](https://github.com/DiegoLinares11/RepasoMLOps/releases/tag/videos)

## 🧱 Conocimiento previo

### 1. Sistema operativo, kernel y procesos

- El **kernel** es el núcleo del sistema operativo: el programa que habla con el
  hardware (CPU, memoria, disco, red) y reparte esos recursos entre los programas.
- Un **proceso** es un programa en ejecución. `python entrenar.py` crea un proceso.
- Encima del kernel hay "todo lo demás": la estructura de carpetas, las librerías del
  sistema (por ejemplo `libpq` para hablar con Postgres, `glibc`), los programas
  instalados. A ese conjunto se le llama **userland** o distribución (Debian, Ubuntu,
  Alpine...).

Docker se apoya en esta separación: **varios "userlands" distintos pueden correr sobre
un mismo kernel**.

### 2. Máquina virtual

Una máquina virtual (VirtualBox, VMware, Hyper-V) simula una **computadora entera**:
CPU, disco, red. Dentro instalas un sistema operativo completo, con **su propio
kernel**. Por eso pesa gigas y tarda minutos en arrancar.

### 3. Puertos y `localhost`

Un **puerto** es un número (0–65535) que identifica a qué programa va dirigida una
conexión de red dentro de una máquina. Un servidor web "escucha" en un puerto: la API de
la Actividad 4 escucha en el **8000**.

- `localhost` (o `127.0.0.1`) = "esta misma máquina".
- `http://localhost:8000` = "el programa que escucha en el puerto 8000 de mi compu".
- `0.0.0.0` como dirección de escucha = "acepto conexiones que lleguen por cualquier
  interfaz", no solo desde la misma máquina.

### 4. API HTTP en una línea

Una API web es un programa que recibe **peticiones HTTP** y responde (normalmente en
JSON). Los métodos que usamos: **GET** (pedir información: `GET /salud`) y **POST**
(enviar datos para que haga algo: `POST /predecir` con el partido en el cuerpo).
**FastAPI** es la librería de Python con la que se escribió la API, y **uvicorn** el
servidor que la ejecuta.

### 5. Variables de entorno (repaso del tema 08)

Pares `NOMBRE=valor` que un programa lee al arrancar (`os.getenv("DIR_MODELOS")`).
Permiten configurar el **mismo** programa de formas distintas sin tocar el código. En
Docker son la forma estándar de pasar configuración a un contenedor.

### 6. Usuarios y permisos en Linux

En Linux cada archivo tiene un **dueño** y permisos. **root** es el administrador: puede
todo. Un programa que corre como root y es atacado le da al atacante control total; por
eso se recomienda correr como un usuario sin privilegios (en la Actividad 4, `mlops`
con uid 1000).

### 7. Qué no resolvía el ambiente virtual (tema 07)

Un venv aísla **librerías de Python**. No fija la versión de Python instalada, ni el
sistema operativo, ni las librerías del sistema. Ahí entra Docker.

## 🎯 Qué tienes que saber

### 1. El problema: el ambiente completo, no solo Python

En la Actividad 3, el mismo código con `random_state=42` dio en `GridSearchCV` un
`f1_macro` de **0.563 en Windows** y **0.611 en macOS**: cada compu tenía otra versión
de scikit-learn. Y aunque fijes todo en un `requirements.txt`, siguen variando la versión
de Python, el sistema operativo y las librerías del sistema que algunas dependencias
necesitan (`psycopg` necesita `libpq`, numpy usa librerías de álgebra lineal).

**Docker empaqueta la aplicación junto con su sistema operativo, sus librerías y sus
versiones exactas**, para que corra idéntica en cualquier máquina. Como dice el PDF de
la Actividad 4: *fijar la semilla no alcanza para reproducir un experimento; hay que
fijar también el entorno completo.*

**Analogía:** un `requirements.txt` es mandar la receta; un venv es darle a cada
receta su alacena; una imagen de Docker es mandar **la cocina entera**, con la estufa,
las ollas y los ingredientes ya medidos.

### 2. Contenedor vs máquina virtual

Un contenedor **no es una máquina virtual pequeña**. Es un **proceso normal** del
sistema anfitrión, aislado con dos funciones del kernel de Linux:

- **namespaces**: hacen que el proceso vea **su propio** sistema de archivos, su propia
  red y su propia lista de procesos (cree que está solo en la máquina).
- **cgroups**: limitan cuánta CPU y memoria puede usar.

| | Máquina virtual | Contenedor |
|---|---|---|
| Qué virtualiza | El hardware completo | Solo el proceso |
| Sistema operativo | Cada VM lleva el suyo entero, **con su kernel** | **Comparten el kernel** del anfitrión |
| Tamaño típico | Gigabytes | Decenas o cientos de MB |
| Arranque | Minutos | Segundos |
| Aislamiento | Total | A nivel de proceso |
| En una laptop caben | 2 o 3 | Decenas |

**¿Y en Windows?** Los contenedores de Linux necesitan un kernel Linux. Docker Desktop
corre un Linux liviano dentro de **WSL2** y ahí viven los contenedores, compartiendo
**ese** kernel. Por eso la Actividad 4 se probó "sobre Windows 11 + WSL2".

### 3. Dockerfile, imagen y contenedor

| Concepto | Qué es | Analogía del PDF | Analogía de programación |
|---|---|---|---|
| **Dockerfile** | La receta: instrucciones para construir | El plano de una casa | El código fuente de una clase |
| **Imagen** | El resultado, **inmutable** y de solo lectura | La casa construida | La **clase** |
| **Contenedor** | Una imagen **en ejecución**, con una capa escribible encima | La casa habitada | Un **objeto** (instancia) |

De una imagen salen **muchos** contenedores, igual que de una clase salen muchos
objetos. La imagen **nunca cambia**: lo que un contenedor escribe va a una **capa
temporal** encima, que **se borra con el contenedor**. De ahí nace toda la discusión de
volúmenes (sección 8).

Otra analogía: la imagen es el **plato congelado** que sale de fábrica; el contenedor es
ese plato **calentado y servido**. Puedes servir diez platos del mismo lote, y lo que le
agregues a uno no cambia los demás ni el lote.

### 4. Capas y caché: por qué `requirements.txt` va antes que el código

Cada instrucción del Dockerfile genera una **capa**. Docker guarda las capas en caché y
reutiliza una capa **solo si ella y todas las anteriores no cambiaron**. En cuanto una
capa cambia, todas las de abajo se reconstruyen.

```dockerfile
COPY entrenador/requirements.txt ./requirements.txt   # cambia poco  -> capa cacheada
RUN pip install --no-cache-dir -r requirements.txt     # la instrucción LENTA
COPY entrenador/entrenar.py ./                         # cambia mucho -> capa barata
```

Con este orden, editar `entrenar.py` solo reconstruye las últimas capas y `pip install`
sale de la caché. Con el orden invertido (copiar el código primero), cada cambio de una
línea reinstalaría scikit-learn completo. El notebook lo simula paso a paso con el
Dockerfile real: con el orden real el `RUN pip install` sale `HIT`; con el orden ingenuo,
`MISS`.

**Regla:** lo que cambia poco arriba, lo que cambia mucho abajo.

### 5. El Dockerfile instrucción por instrucción

| Instrucción | Qué hace | Cuándo corre | En la Actividad 4 |
|---|---|---|---|
| `FROM` | Imagen base de la que se parte | Build | `FROM python:3.12-slim` (versión fija: `python:3.12` a secas cambiaría con el tiempo) |
| `ENV` | Variable de entorno grabada en la imagen | Build y ejecución | `PYTHONUNBUFFERED=1` (logs en vivo), `PYTHONDONTWRITEBYTECODE=1` (sin `.pyc`) |
| `WORKDIR` | "cd" dentro de la imagen (la crea si no existe) | Build y ejecución | `WORKDIR /app` |
| `COPY` | Copia archivos del **contexto** a la imagen | Build | `COPY entrenador/requirements.txt ./requirements.txt` |
| `ADD` | Como `COPY` pero también descomprime `.tar` y baja URLs | Build | No se usa (preferir `COPY`) |
| `RUN` | Ejecuta un comando y guarda el resultado como capa | **Build** | `RUN pip install ... && rm /tmp/*.whl` |
| `USER` | Usuario con el que corren los siguientes pasos y el contenedor | Build y ejecución | `USER mlops` |
| `EXPOSE` | **Documenta** el puerto en que escucha; no publica nada | (metadato) | `EXPOSE 8000` (solo la API) |
| `CMD` | Comando **por defecto** al arrancar el contenedor | **Ejecución** | `CMD ["python", "entrenar.py"]`, `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]` |
| `ENTRYPOINT` | Ejecutable **fijo** del contenedor | Ejecución | No se usa |
| `ARG` | Variable que solo existe durante el build | Build | No se usa |

**`RUN` vs `CMD`**: `RUN` se ejecuta **al construir** la imagen (instalar cosas);
`CMD` se ejecuta **al arrancar** cada contenedor (lanzar la app).

**`CMD` vs `ENTRYPOINT`**:

| Dockerfile | `docker run imagen` | `docker run imagen python -c "print(1)"` |
|---|---|---|
| `CMD ["uvicorn", "main:app"]` | ejecuta uvicorn | **reemplaza** el CMD: ejecuta `python -c "print(1)"` |
| `ENTRYPOINT ["python"]` + `CMD ["entrenar.py"]` | `python entrenar.py` | `python python -c ...` (lo que escribes se **agrega** como argumentos al ENTRYPOINT) |

Usa `CMD` cuando quieras un comando por defecto fácil de cambiar (lo normal en un
servicio); `ENTRYPOINT` cuando el contenedor "es" un programa y lo que escribes son sus
argumentos.

**Forma exec vs forma shell**: `CMD ["python", "entrenar.py"]` (lista JSON, forma
*exec*) ejecuta python directamente como proceso principal y recibe las señales de
`docker stop`. `CMD python entrenar.py` (forma *shell*) lo envuelve en `/bin/sh -c` y las
señales pueden no llegar. Preferir siempre la forma exec.

**Detalles de buena práctica en los Dockerfiles reales:**

- `pip install --no-cache-dir`: no guardar la caché de descargas dentro de la imagen.
- `&& rm /tmp/*.whl` **en el mismo `RUN`**: si fuera en otro, el archivo seguiría
  ocupando espacio en la capa anterior.
- Usuario sin privilegios (`useradd --uid 1000 mlops` + `USER mlops`).
- `uvicorn --host 0.0.0.0`: con el valor por defecto `127.0.0.1` la API solo aceptaría
  conexiones desde **dentro** del contenedor y `localhost:8000` no respondería.

Los dos Dockerfiles comentados línea por línea:
[`ejemplos/entrenador/Dockerfile`](ejemplos/entrenador/Dockerfile) y
[`ejemplos/api/Dockerfile`](ejemplos/api/Dockerfile).

### 6. El contexto de construcción y `.dockerignore`

`docker build -f entrenador/Dockerfile .` manda a Docker toda la carpeta `.` (el
**contexto**). Un `COPY` solo ve archivos **dentro** del contexto. Por eso en la
Actividad 4 el contexto es la raíz del repo y no `entrenador/`: el Dockerfile necesita
también `libreria/act3_pipeline-0.1.0-py3-none-any.whl`.

`.dockerignore` excluye cosas del contexto, como un `.gitignore` para Docker. El de la
Actividad 4 saca `.git`, los `.md`, `capturas/`, `__pycache__/` y, sobre todo, **`.env`**:
si el archivo con la contraseña entrara al contexto, un `COPY . .` lo metería dentro de
la imagen y cualquiera con la imagen podría leerlo. Ver
[`ejemplos/.dockerignore`](ejemplos/.dockerignore).

### 7. Los comandos básicos

| Comando | Qué hace |
|---|---|
| `docker build -t act4/api:1.0 -f api/Dockerfile .` | Construir una imagen y ponerle nombre:etiqueta |
| `docker images` | Listar imágenes |
| `docker run --rm -p 8000:8000 act4/api:1.0` | Crear y arrancar un contenedor (`--rm`: borrarlo al terminar) |
| `docker run -d --name api -e DIR_MODELOS=/modelos act4/api:1.0` | En segundo plano (`-d`), con nombre y variable de entorno |
| `docker ps` / `docker ps -a` | Contenedores corriendo / también los detenidos |
| `docker logs -f act4-api` | Ver (y seguir) la salida de un contenedor |
| `docker exec -it act4-api sh` | Abrir una terminal **dentro** de un contenedor que corre |
| `docker stop act4-api` / `docker rm act4-api` | Detener / borrar un contenedor |
| `docker rmi act4/api:1.0` | Borrar una imagen |
| `docker volume ls` / `docker volume inspect actividad4-mlops_modelos` | Listar volúmenes / ver dónde viven |
| `docker system df` / `docker system prune` | Cuánto ocupa Docker / limpiar lo que nadie usa |

Funcionan igual en PowerShell y en bash. Lo que cambia es el salto de línea en comandos
largos (`` ` `` en PowerShell, `\` en bash) y la carpeta actual para un bind mount
(`${PWD}` en PowerShell, `$(pwd)` en bash).

### 8. Persistencia: capa escribible, volúmenes y bind mounts

El sistema de archivos de un contenedor es la imagen (solo lectura) más una **capa
escribible** que **pertenece al contenedor** y muere con él. Si el entrenador guardara
el modelo en `/app/modelo.joblib`, al terminar desaparecería y la API nunca lo vería. Si
Postgres escribiera ahí, cada `docker compose down` borraría la base.

| Forma | Dónde vive | ¿Sobrevive al contenedor? | Cuándo usarla |
|---|---|---|---|
| Capa escribible | Dentro del contenedor | **No** | Archivos temporales |
| **Volumen con nombre** | Área administrada por Docker | Sí | Datos que produce la app: bases de datos, modelos |
| **Bind mount** | Una carpeta de **tu** compu | Sí | Código, datos de entrada, configuración |
| tmpfs | Memoria RAM | Nunca toca el disco | Secretos y temporales |

| | Volumen con nombre | Bind mount |
|---|---|---|
| Sintaxis en compose | `modelos:/modelos` (un nombre) | `./datos:/datos` (empieza con `./` o `/`) |
| Lo administra | Docker | Tú |
| Ruta | Irrelevante para ti | Depende de cada máquina |
| Portabilidad | Alta | Baja |
| Rendimiento en Docker Desktop | Mejor | Peor |
| Ideal para | Bases de datos, modelos | Código, datos de entrada |

**Regla práctica del PDF:** *si lo produce la aplicación, volumen con nombre; si lo
escribe el desarrollador, bind mount.*

**`:ro` (solo lectura)**: `./datos:/datos:ro` impide que el entrenador modifique tus
datos; `modelos:/modelos:ro` impide que la API altere el modelo (mínimo privilegio).

**El bug real de la Actividad 4 (permisos):** el primer arranque entrenó bien pero falló
al guardar con `PermissionError: [Errno 13] Permission denied: '/modelos/modelo.joblib'`.
Cuando Docker monta un volumen con nombre **vacío**, copia el dueño y los permisos que
esa carpeta tiene **en la imagen**; si la carpeta no existe en la imagen, el volumen nace
como `root` y el usuario `mlops` no puede escribir. Solución: crear la carpeta en la
imagen con el dueño correcto (`mkdir -p /modelos && chown -R mlops:mlops /app /modelos`)
y borrar el volumen viejo con `docker compose down -v` para que naciera de nuevo. *Un
volumen recuerda su propietario igual que recuerda sus datos.*

**Por qué el modelo no va dentro de la imagen:** reentrenar obligaría a reconstruir y
redistribuir la imagen; las imágenes deben ser inmutables y reproducibles (entrenar
durante el build las ata a los datos del momento); y el modelo es **estado**, no código.

### 9. Redes: los servicios se llaman por su nombre

Compose crea una red privada (`red-mlops`, tipo `bridge`) y un **DNS interno**: cada
servicio es alcanzable por su **nombre**. Por eso la API se conecta a
`postgresql://...@db:5432/...`: literalmente `db`, sin IPs.

| | `ports: - "8000:8000"` | `EXPOSE 8000` | Sin nada |
|---|---|---|---|
| Accesible desde tu navegador | **Sí** (`localhost:8000`) | No | No |
| Accesible desde otros contenedores de la red | Sí | Sí | Sí |
| Qué hace | Publica `PUERTO_TU_COMPU:PUERTO_CONTENEDOR` | Solo documenta | — |

En la Actividad 4 **solo la API publica puerto**; Postgres no tiene `ports`, así que es
inalcanzable desde fuera aunque los contenedores lo vean.

**El error clásico:** dentro de un contenedor, `localhost` es **el propio contenedor**.
Si la API intentara conectarse a `localhost:5432`, buscaría Postgres dentro de sí misma y
fallaría. Entre contenedores se usa el **nombre del servicio**.

### 10. Docker Compose

Docker maneja un contenedor a la vez; la Actividad 4 tiene tres con dependencias reales
(la API no sirve sin modelo y no guarda nada sin base). **Compose describe el sistema
completo en un YAML y lo levanta en orden con un comando.** Además resuelve cuatro cosas:

1. **Red privada automática** con DNS por nombre de servicio.
2. **Orden de arranque real** con `depends_on` + condiciones:
   `service_completed_successfully` (la API espera a que el entrenador **termine con
   código 0**) y `service_healthy` (espera a que el `healthcheck` de Postgres pase).
   Sustituye al "esperar cinco segundos y confiar".
3. **Configuración por variables de entorno** leídas de un `.env` que no se versiona.
4. **Aislamiento hacia el exterior**: solo se publica lo que tú decides.

| Clave del YAML | Para qué |
|---|---|
| `name` | Prefijo de todo lo que se crea (`actividad4-mlops_modelos`) |
| `services.<x>.build` | Construir desde un Dockerfile (`context` + `dockerfile`) |
| `services.<x>.image` | Imagen a usar (o nombre de la que se construye) |
| `environment` | Variables de entorno del contenedor |
| `${VAR:-defecto}` | Toma `VAR` del `.env`; si no está, usa `defecto` |
| `ports` | Publicar puertos hacia tu compu |
| `volumes` | Montar volúmenes y bind mounts |
| `depends_on` | Orden de arranque (con condiciones) |
| `healthcheck` | Comando que dice si el servicio está **listo**, no solo corriendo |
| `restart` | `"no"` (lotes), `unless-stopped`, `always`, `on-failure` |
| `networks` / `volumes` (raíz) | Declarar redes y volúmenes con nombre |

| Comando | Qué hace |
|---|---|
| `docker compose up --build` | Construir las imágenes y levantar todo |
| `docker compose up -d` | Levantar en segundo plano |
| `docker compose ps` / `ps -a` | Estado de cada servicio |
| `docker compose logs -f api` | Seguir los logs de un servicio |
| `docker compose exec api sh` | Terminal dentro del servicio |
| `docker compose config` | Ver el YAML final con las variables ya reemplazadas |
| `docker compose up --scale api=3` | Varias copias de un servicio (sin `container_name` fijo) |
| `docker compose down` | Apagar y borrar contenedores y red (**los volúmenes se quedan**) |
| `docker compose down -v` | Apagar y borrar **también los volúmenes** (destructivo) |

El compose real comentado línea por línea: [`ejemplos/docker-compose.yml`](ejemplos/docker-compose.yml).

### 11. Variables de entorno, `.env` y secretos

- El **`.env`** (junto al `docker-compose.yml`) lo lee Compose automáticamente para
  reemplazar `${...}`. Al repo va solo [`ejemplos/.env.example`](ejemplos/.env.example).
- El `.env` también va en el **`.dockerignore`**: no debe terminar dentro de una imagen.
- Las variables llegan al contenedor por `environment:` y el código las lee con
  `os.getenv` (`DIR_MODELOS`, `URL_BD`, `N_ITER`, `FORZAR_REENTRENO`). Así la **misma
  imagen** sirve en desarrollo y en producción.
- Limitación reconocida en el PDF: la contraseña viaja como variable de entorno; en
  producción lo correcto es usar **secrets** (Docker secrets, un gestor de secretos).

### 12. Monolito vs microservicios, lote vs servicio

En la Actividad 3 todo era **un solo programa**: leer CSV, calibrar, evaluar, imprimir.
Funciona en una laptop, pero en producción entrenar tarda minutos y consume CPU, mientras
que una predicción debe responder en milisegundos. Si comparten proceso, cada
reentrenamiento deja la app sin responder.

| | Monolito | Microservicios |
|---|---|---|
| Despliegue | Todo junto | Cada servicio por separado |
| Escalar | Todo o nada | Solo lo que lo necesita (`--scale api=3`) |
| Un fallo | Tumba todo | Queda aislado (si Postgres cae, la API sigue prediciendo) |
| Imágenes | Una grande | Pequeñas y específicas (la API no necesita el dataset) |
| Complejidad | Baja | Más piezas, red, orden de arranque |

Ojo con el ejemplo de escalado del PDF: con el `docker-compose.yml` tal cual,
`docker compose up --scale api=3` **no funciona**, porque la API tiene un
`container_name` fijo (`act4-api`, dos contenedores no pueden llamarse igual) y publica
el puerto fijo `8000` de tu compu (solo uno puede ocuparlo). Para escalar hay que quitar
`container_name` y publicar un rango (`"8000-8002:8000"`) o poner un balanceador
delante. Está como reto en [`ejercicios.md`](ejercicios.md).

| | Trabajo por lotes (*batch*) | Servicio |
|---|---|---|
| Ejemplo | `entrenador` | `api`, `db` |
| Ciclo de vida | Corre, termina y **muere** (`Exited (0)`) | Siempre encendido |
| `restart` | `"no"` | `unless-stopped` |
| Ritmo | Pesado y esporádico | Liviano y constante |

## 📂 Qué hicimos en el curso

**Actividad 4: Docker, Docker Compose y microservicios**
([Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS), PDF
`Actividad_4_MLOPS.pdf`). Diego Linares, Andy Fuentes, Christian Echeverria y Diederich
Solis, 18 de agosto de 2026.

El pipeline calibrado en la Actividad 3 se repartió en **tres contenedores** que se
levantan con `docker compose up --build`:

```
   ./datos (CSV) ──►  entrenador  ──escribe──►  ╔ volumen: modelos ╗
   bind mount, ro     corre y muere             ╚════════╤═════════╝
                                                         │ lee (ro)
   puerto 8000  ────►  api (FastAPI)  ──guarda──►  db (Postgres)
   único expuesto      siempre encendida           ╚ volumen: pgdata ╝
```

| Servicio | Tipo | Qué hace | Ciclo de vida |
|---|---|---|---|
| `entrenador` | Lote | Lee el CSV por bind mount `:ro`, calibra con `RandomizedSearchCV` (60 combinaciones, `f1_macro`), guarda `modelo.joblib` + `metadatos.json` en el volumen `modelos` | Corre y muere; si el modelo ya existe en el volumen, no reentrena (salvo `FORZAR_REENTRENO=1`) |
| `api` | Servicio | FastAPI: carga el modelo del volumen en `:ro`, expone `/salud`, `/modelo`, `/predecir`, `/predicciones` en el puerto 8000, guarda cada predicción en Postgres | Siempre encendida |
| `db` | Estado | Postgres 16 (`postgres:16-alpine`), tabla `predicciones` creada por `db/init.sql`, datos en el volumen `pgdata` | Siempre encendida |

**El detalle técnico clave:** las **dos** imágenes instalan el mismo wheel
`act3_pipeline-0.1.0` y fijan las **mismas versiones exactas** (scikit-learn 1.8.0,
pandas 2.3.3, numpy 2.4.1, scipy 1.17.1, joblib 1.5.3), porque el `modelo.joblib` guarda
la **ruta de import** de los transformadores propios `PorcentajeATexto` y `RatioATexto`,
no su código. Sin el paquete, la API no podría cargar el modelo.

**Resultados reales** (Docker Engine 29.7.2 / Compose v5.4.0 sobre Windows 11 + WSL2):

| | Windows (Act. 3) | macOS (Act. 3) | Contenedor (Act. 4) |
|---|---|---|---|
| Modelo ganador | LogisticRegression | LogisticRegression | LogisticRegression |
| `f1_macro` en CV | 0.619 | 0.619 | 0.619 |
| Accuracy en test | 0.690 | 0.690 | 0.690 |
| `f1_macro` en test | 0.631 | 0.631 | 0.631 |

Baseline (clase mayoritaria): accuracy 0.483 / `f1_macro` 0.217. La diferencia con la
Act. 3 es la **garantía**: allá coincidieron por suerte (las búsquedas con Random Forest
daban 0.563 vs 0.611); aquí la imagen fija scikit-learn 1.8.0, pandas 2.3.3 y Python
3.12.14 para todos. (El entrenador solo corre `RandomizedSearchCV`, la búsqueda ganadora
de la Act. 3.)

**Predicciones de prueba** (partidos del dataset, ambas correctas):
Real Madrid vs Marseille (real 2-1) → `Home Win` con 0.8764; Ajax vs Inter (real 0-2) →
`Away Win` con 0.7822.

**Las tres pruebas de persistencia:**

1. **El modelo sobrevive a su creador.** `api` y `db` en `Up (healthy)`, `entrenador` en
   `Exited (0)`, y `/salud` responde `"modelo_cargado": true`. Los metadatos dicen que lo
   entrenó el contenedor `3e635acd60eb`, que ya no existe.
2. **La base sobrevive a un apagado completo.** Tras `docker compose down`, los volúmenes
   `actividad4-mlops_modelos` y `actividad4-mlops_pgdata` siguen. Al hacer `up -d`, un
   entrenador **nuevo** (`8910543744d3`) encuentra el modelo y no reentrena, y
   `/predicciones` mantiene `total_historico: 2`.
3. **Sin volúmenes no queda nada.** `docker compose down -v` borra ambos volúmenes; al
   levantar, el entrenador calibra de cero (14.9 s, CV 0.619, modelo de 10 KB) y
   `total_historico: 0`.

**El bug de permisos** (sección 8): `PermissionError` al guardar en `/modelos` por correr
como usuario sin privilegios sobre un volumen que nació como `root`. Se arregló con
`mkdir -p /modelos && chown` en la imagen y `docker compose down -v`.

**Conclusiones del PDF:** Docker eliminó de raíz la discrepancia Windows/macOS; el
empaquetado de la Act. 3 rindió aquí (sin el wheel la API no reconstruye el pipeline);
separar entrenamiento y servicio es la decisión de arquitectura central; sin volúmenes un
contenedor no recuerda nada; `depends_on` con condiciones reemplaza esperas arbitrarias;
correr sin privilegios exige preparar los volúmenes.

**Limitaciones y trabajo futuro:** el entrenador corre una sola vez (en producción sería
una tarea programada o disparada por datos nuevos); la API carga el modelo al arrancar,
así que reentrenar exige reiniciarla; el modelo no tiene versionado (un registro como
MLflow sería el siguiente paso, tema 11); la contraseña viaja como variable de entorno
(lo correcto serían *secrets*); y el modelo usa estadísticas que solo se conocen al
terminar el partido, así que explica más de lo que predice.

## 🧪 Práctica

**`repaso.ipynb`** (ya ejecutado, generado desde `repaso.py`). No necesita Docker:

1. Lee el Dockerfile real del entrenador y clasifica sus 10 instrucciones.
2. **Simula la caché de capas**: primera construcción (todo `MISS`), y tras editar
   `entrenar.py`, orden real (`pip install` en `HIT`) vs orden ingenuo (`pip install` en
   `MISS`).
3. Simula **imagen / contenedor / capa escribible** con `ChainMap` y `MappingProxyType`.
4. Simula el **volumen** `modelos` (el modelo sobrevive al entrenador, la API lo lee en
   `:ro`) y la diferencia `down` / `down -v`.
5. Lee el `docker-compose.yml` real: tabla de servicios, puertos, volúmenes y
   `depends_on`; orden de arranque con `graphlib`.
6. Reemplaza `${VAR:-defecto}` con y sin el `.env.example`.

```powershell
python tools/build_nb.py 09-docker/repaso.py
```

**`ejemplos/`** (copias comentadas línea por línea de los archivos reales de la Actividad 4):

| Archivo | Qué es |
|---|---|
| [`docker-compose.yml`](ejemplos/docker-compose.yml) | Los tres servicios, la red y los volúmenes |
| [`entrenador/Dockerfile`](ejemplos/entrenador/Dockerfile) | Imagen del trabajo por lotes (caché, usuario, permisos del volumen) |
| [`api/Dockerfile`](ejemplos/api/Dockerfile) | Imagen de la API (EXPOSE, CMD vs ENTRYPOINT, `--host 0.0.0.0`) |
| [`api/main.py`](ejemplos/api/main.py) | La API de FastAPI: endpoints, validación con pydantic, Postgres |
| [`.dockerignore`](ejemplos/.dockerignore) | Qué no entra al contexto de construcción |
| [`.env.example`](ejemplos/.env.example) | Variables que lee Compose |
| [`db/init.sql`](ejemplos/db/init.sql) | Tabla de predicciones (corre solo con el volumen vacío) |

Son copias para leer; para levantar el sistema hace falta el repo original completo
(trae `datos/`, `libreria/*.whl` y `entrenador/entrenar.py`).

**[`ejercicios.md`](ejercicios.md)**: comandos y retos para hacer con Docker Desktop.

## ❓ Preguntas tipo examen

**P:** ¿Qué problema resuelve Docker que un ambiente virtual no resuelve?
**R:** Un venv solo aísla las librerías de Python. Docker empaqueta el ambiente completo: sistema operativo, versión de Python, librerías del sistema y de Python con versiones exactas, y el código. Por eso el resultado fue idéntico en Windows, macOS y el contenedor (CV 0.619, accuracy 0.690).

**P:** ¿Por qué un contenedor no es una máquina virtual?
**R:** Porque no virtualiza hardware ni lleva su propio kernel: es un proceso del anfitrión aislado con namespaces (su propia vista de archivos, red y procesos) y limitado con cgroups. Comparte el kernel, por eso pesa MB y arranca en segundos.

**P:** Diferencia entre Dockerfile, imagen y contenedor.
**R:** El Dockerfile es la receta; la imagen es el resultado de construirla, inmutable y de solo lectura (la clase); el contenedor es una imagen en ejecución con una capa escribible encima (un objeto). De una imagen salen muchos contenedores.

**P:** ¿Por qué se copia `requirements.txt` e instala antes de copiar el código?
**R:** Por la caché de capas: una capa se reutiliza solo si ella y todas las anteriores no cambiaron. Así, editar el código solo reconstruye las últimas capas y el `pip install` (lento) sale de la caché.

**P:** Diferencia entre `RUN` y `CMD`.
**R:** `RUN` se ejecuta al construir la imagen y guarda su resultado como capa (instalar dependencias). `CMD` es el comando que se ejecuta al arrancar cada contenedor (lanzar la app).

**P:** Diferencia entre `CMD` y `ENTRYPOINT`.
**R:** `CMD` es el comando por defecto y se reemplaza completo si pasas otro comando en `docker run`. `ENTRYPOINT` fija el ejecutable y lo que pases se agrega como argumentos (y el `CMD` actúa como argumentos por defecto).

**P:** ¿`EXPOSE 8000` hace que la API sea accesible desde el navegador?
**R:** No. Solo documenta el puerto. Lo que lo publica es `ports: - "8000:8000"` en el compose o `-p 8000:8000` en `docker run`.

**P:** ¿Qué pasa con un archivo que un contenedor escribe fuera de cualquier volumen cuando el contenedor se borra?
**R:** Se pierde: estaba en la capa escribible, que pertenece al contenedor. Por eso el entrenador guarda el modelo en el volumen `modelos` y Postgres en `pgdata`.

**P:** Volumen con nombre vs bind mount: ¿cuándo usar cada uno?
**R:** Volumen con nombre (lo administra Docker, portable) para lo que produce la aplicación: base de datos, modelos. Bind mount (una carpeta de tu compu) para lo que escribe el desarrollador: código, datos de entrada, configuración. En la Act. 4: `./datos:/datos:ro` y `modelos:/modelos`.

**P:** ¿Qué diferencia hay entre `docker compose down` y `docker compose down -v`?
**R:** `down` borra contenedores y red pero conserva los volúmenes (el modelo y el historial sobreviven). `down -v` borra también los volúmenes: el entrenador recalibra de cero y el historial queda en 0.

**P:** ¿Cómo se conecta la API a Postgres sin conocer su IP?
**R:** Por el nombre del servicio: `postgresql://...@db:5432/...`. Compose crea una red privada con DNS interno que traduce `db` a la IP del contenedor.

**P:** ¿Por qué la API no puede usar `localhost:5432` para conectarse a la base?
**R:** Porque dentro de un contenedor `localhost` es el propio contenedor; Postgres está en otro. Entre contenedores se usa el nombre del servicio.

**P:** ¿Qué hacen `service_completed_successfully` y `service_healthy` en `depends_on`?
**R:** La API espera a que el entrenador termine con código de salida 0 (el modelo existe) y a que el healthcheck de Postgres pase (acepta conexiones). Es un orden de arranque real, no una espera arbitraria.

**P:** ¿Por qué la API instala el paquete `act3_pipeline` si no entrena nada?
**R:** Porque `joblib`/pickle guarda la ruta de import de las clases, no su código. Al cargar `modelo.joblib` Python necesita importar `PorcentajeATexto` y `RatioATexto` desde `act3_pipeline`, con las mismas versiones exactas que usó el entrenador.

**P:** ¿Por qué apareció `PermissionError` al guardar el modelo y cómo se arregló?
**R:** El contenedor corre como `mlops` (no root) y el volumen vacío nació como `root` porque `/modelos` no existía en la imagen (Docker copia dueño y permisos de la carpeta de la imagen). Se creó `/modelos` con `chown mlops` en el Dockerfile y se borró el volumen con `down -v` para recrearlo.

**P:** ¿Por qué no hornear el modelo dentro de la imagen?
**R:** Reentrenar obligaría a reconstruir y redistribuir la imagen; las imágenes deben ser inmutables y reproducibles; el modelo es estado, no código, y se versiona distinto.

**P:** ¿Qué ventajas concretas dio separar entrenador y API?
**R:** Escalado independiente (`--scale api=3`), reentrenar sin interrumpir el servicio, imágenes más pequeñas y específicas, y fallos aislados (si Postgres cae, la API sigue prediciendo).

**P:** ¿Para qué sirve `.dockerignore`?
**R:** Excluye archivos del contexto de construcción: acelera el build, evita invalidar la caché por cambios irrelevantes y, sobre todo, impide que secretos como `.env` terminen dentro de la imagen.

## 🏋️ Ejercicios

Detallados en [`ejercicios.md`](ejercicios.md). Resumen:

1. **Primeros pasos**: `docker run hello-world`, `python:3.12-slim` interactivo, `ps`,
   `logs`, `exec`, `rm`.
2. **Tu primera imagen** con el paquete de la Tarea 4 instalado desde TestPyPI.
3. **Caché en vivo**: cambia una línea del código y mide el rebuild con el orden bueno y
   con el malo.
4. **Levanta la Actividad 4** y repite las tres pruebas de persistencia.
5. **Retos**: escalar la API, provocar el bug de permisos, romper el DNS con `localhost`.

## 🔗 Referencias

- Docs oficiales de Docker: <https://docs.docker.com/get-started/>
- Referencia del Dockerfile: <https://docs.docker.com/reference/dockerfile/>
- Caché de construcción: <https://docs.docker.com/build/cache/>
- Volúmenes y bind mounts: <https://docs.docker.com/engine/storage/volumes/> · <https://docs.docker.com/engine/storage/bind-mounts/>
- Redes en Compose: <https://docs.docker.com/compose/how-tos/networking/>
- Referencia de Compose (`depends_on`, `healthcheck`): <https://docs.docker.com/reference/compose-file/services/>
- Variables y `.env` en Compose: <https://docs.docker.com/compose/how-tos/environment-variables/>
- Docker Desktop con WSL2: <https://docs.docker.com/desktop/features/wsl/>
- Imagen oficial de Postgres (`/docker-entrypoint-initdb.d`): <https://hub.docker.com/_/postgres>
- FastAPI: <https://fastapi.tiangolo.com/> · FastAPI en contenedores: <https://fastapi.tiangolo.com/deployment/docker/>
- Repos: [Actividad4-MLOPS](https://github.com/DiegoLinares11/Actividad4-MLOPS), [Actividad3-MLOPS](https://github.com/DiegoLinares11/Actividad3-MLOPS), [Tarea4-MLOPS](https://github.com/DiegoLinares11/Tarea4-MLOPS)
