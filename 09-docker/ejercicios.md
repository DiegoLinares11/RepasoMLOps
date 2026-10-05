# 09 · Ejercicios en tu compu: Docker y Compose

Necesitas **Docker Desktop** con el backend de **WSL2** (Windows) o Docker Engine
(Linux/macOS). Comprueba la instalación:

```powershell
docker version
docker compose version
docker run --rm hello-world
```

Los comandos de Docker son iguales en PowerShell y en bash. Cambian tres cosas:

| | PowerShell | bash |
|---|---|---|
| Continuar un comando en otra línea | `` ` `` al final | `\` al final |
| Carpeta actual (para bind mounts) | `${PWD}` | `$(pwd)` |
| Pedir una URL | `Invoke-RestMethod` o `curl.exe` (en PowerShell 5, `curl` es un alias de `Invoke-WebRequest`) | `curl` |

---

## Ejercicio 1 · Primeros pasos con contenedores

```powershell
docker pull python:3.12-slim
docker images
# Un contenedor interactivo (-it) que se borra al salir (--rm)
docker run --rm -it python:3.12-slim python -c "import sys, platform; print(sys.version, platform.platform())"
# Uno en segundo plano (-d) con nombre, que imprime algo cada 2 segundos
docker run -d --name reloj python:3.12-slim python -u -c "import time,datetime; [print(datetime.datetime.now(), flush=True) or time.sleep(2) for _ in range(1000)]"
docker ps
docker logs -f reloj            # Ctrl+C para dejar de seguir (el contenedor sigue)
docker exec -it reloj sh        # terminal DENTRO del contenedor
#   dentro:  hostname ; cat /etc/os-release ; ps aux 2>/dev/null || ls /proc ; exit
docker stop reloj
docker ps -a                    # aparece como Exited
docker rm reloj
```

**Preguntas:**
1. ¿Qué sistema operativo dice `/etc/os-release` dentro del contenedor, si tú estás en
   Windows? ¿Por qué es posible? (Pista: WSL2 y kernel compartido.)
2. ¿Qué devuelve `hostname` dentro? Compáralo con el ID de `docker ps`.
3. Crea un archivo dentro (`docker run --name prueba python:3.12-slim sh -c "echo hola > /nota.txt"`),
   borra el contenedor y crea otro de la misma imagen: ¿existe `/nota.txt`? ¿Por qué no?

---

## Ejercicio 2 · Tu primera imagen: el paquete de la Tarea 4 en un contenedor

Crea una carpeta `act3-docker` con este `Dockerfile` (instala el paquete publicado en el
tema 08):

```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir \
      --index-url https://test.pypi.org/simple/ \
      --extra-index-url https://pypi.org/simple/ \
      act3-pipeline-mlops
CMD ["act3-demo", "--busqueda", "aleatoria"]
```

```powershell
docker build -t act3-demo:0.1.0 .
docker images act3-demo
docker run --rm act3-demo:0.1.0
# Reemplazar el CMD: ver la versión de scikit-learn que quedó instalada
docker run --rm act3-demo:0.1.0 python -c "import sklearn; print(sklearn.__version__)"
```

**Preguntas:**
1. ¿Te dio `accuracy=0.690  f1_macro=0.631` como en la Tarea 4 y la Actividad 4?
2. El `pyproject.toml` del paquete dice `scikit-learn>=1.3`. ¿Qué versión se instaló? Si
   reconstruyes dentro de un año, ¿será la misma? ¿Cómo lo fijarías? (Pista: un
   `requirements.txt` con `==` como el de la Actividad 4.)
3. Agrega `RUN useradd --create-home --uid 1000 mlops` y `USER mlops` antes del `CMD`.
   ¿Sigue funcionando? (act3-demo escribe `pipeline_diagram.html` en `/app`: ¿de quién
   es `/app`?)

---

## Ejercicio 3 · La caché de capas en vivo

En una carpeta nueva crea `requirements.txt` (con `pandas==2.3.3` y `scikit-learn==1.8.0`),
`app.py` (con `print("v1")`) y este Dockerfile **en orden bueno**:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
```

```powershell
Measure-Command { docker build -t cache-bueno . }      # 1a vez: lenta
(Get-Content app.py) -replace 'v1','v2' | Set-Content app.py
Measure-Command { docker build -t cache-bueno . }      # 2a vez: ¿cuánto tardó?
```

```bash
time docker build -t cache-bueno .
sed -i 's/v1/v2/' app.py
time docker build -t cache-bueno .
```

Ahora cambia el Dockerfile al **orden malo** (`COPY . .` antes del `RUN pip install`),
construye una vez, cambia `app.py` otra vez y vuelve a construir.

**Preguntas:** ¿En qué pasos aparece `CACHED` en la salida de cada build? ¿Cuántos
segundos tardó la segunda construcción en cada orden? Compara con la simulación del
notebook de este tema.

---

## Ejercicio 4 · Levantar la Actividad 4 y repetir las tres pruebas

```powershell
git clone https://github.com/DiegoLinares11/Actividad4-MLOPS.git
cd Actividad4-MLOPS
Copy-Item .env.example .env          # y cambia POSTGRES_PASSWORD
docker compose up --build -d
docker compose ps -a                 # api y db healthy, entrenador Exited (0)
docker compose logs entrenador
docker volume ls
```

Abre <http://localhost:8000/docs> y prueba los endpoints. Desde la terminal:

```powershell
Invoke-RestMethod http://localhost:8000/salud
Invoke-RestMethod http://localhost:8000/modelo
$partido = @{
  home_team = "Real Madrid"; away_team = "Marseille"
  home_possession = "43%"; away_possession = "57%"
  home_shots_on_target = "15 of 28"; away_shots_on_target = "5 of 15"
  home_saves = "4 of 5"; away_saves = "13 of 15"
  home_shots_on_target_pct = 53.6; away_shots_on_target_pct = 33.3
  home_saves_pct = 80.0; away_saves_pct = 86.7
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/predecir -ContentType "application/json" -Body $partido
Invoke-RestMethod "http://localhost:8000/predicciones?limite=5"
```

```bash
curl http://localhost:8000/salud
curl -X POST http://localhost:8000/predecir -H "Content-Type: application/json" \
  -d '{"home_team":"Real Madrid","away_team":"Marseille","home_possession":"43%","away_possession":"57%","home_shots_on_target":"15 of 28","away_shots_on_target":"5 of 15","home_saves":"4 of 5","away_saves":"13 of 15","home_shots_on_target_pct":53.6,"away_shots_on_target_pct":33.3,"home_saves_pct":80.0,"away_saves_pct":86.7}'
curl "http://localhost:8000/predicciones?limite=5"
```

**Las tres pruebas del PDF:**

```powershell
# 1) El modelo sobrevive a su creador
docker compose ps -a                          # entrenador: Exited (0)
Invoke-RestMethod http://localhost:8000/modelo   # ...y el modelo sigue ahí

# 2) La base sobrevive a un apagado completo
docker compose down
docker volume ls                              # los dos volúmenes siguen
docker compose up -d
docker compose logs entrenador                # "ya existe /modelos/modelo.joblib ... no se reentrena"
Invoke-RestMethod http://localhost:8000/predicciones   # total_historico igual que antes

# 3) Sin volúmenes no queda nada
docker compose down -v
docker compose up -d
docker compose logs entrenador                # vuelve a calibrar
Invoke-RestMethod http://localhost:8000/predicciones   # total_historico: 0
```

**Preguntas:** ¿Tu predicción de Real Madrid fue `Home Win` con 0.8764 como en el PDF?
¿El campo `atendido_por` coincide con el `CONTAINER ID` de `act4-api` en `docker ps`?

---

## Ejercicio 5 · Retos

1. **Solo lectura de verdad.** `docker compose exec api sh` y dentro:
   `ls -l /modelos` y `touch /modelos/x`. ¿Qué error sale? ¿Qué línea del compose lo causa?
2. **El DNS por nombre.** En una copia del compose, cambia `@db:5432` por `@localhost:5432`
   en la `URL_BD` de la API, `docker compose up -d` y mira `/salud`. ¿Qué dice `base_de_datos`? ¿Y
   `guardado_en_bd` al predecir? ¿Por qué la API **no** se cae? Vuelve a poner `db`.
3. **Reentrenar.** `docker compose run --rm -e FORZAR_REENTRENO=1 -e N_ITER=10 entrenador`.
   ¿Cambia `cv_mejor_score` en `/modelo`? ¿Por qué la API sigue mostrando el modelo viejo
   hasta `docker compose restart api`? (Es una de las limitaciones del PDF.)
4. **Escalar la API.** Prueba `docker compose up -d --scale api=3`. ¿Qué error da y por
   qué? Arréglalo en una copia del compose: quita `container_name: act4-api` y cambia
   `ports` a `"8000-8002:8000"`. Pide `/salud` a los puertos 8000, 8001 y 8002: ¿cambia
   `contenedor`?
5. **Provoca el bug de permisos.** En una copia de `entrenador/Dockerfile`, quita
   `&& mkdir -p /modelos` y `/modelos` del `chown`. `docker compose down -v` y
   `docker compose up --build`. ¿Sale el `PermissionError: [Errno 13]`? Restaura el
   Dockerfile: ¿basta con reconstruir o también hay que hacer `down -v`? ¿Por qué?
6. **Dónde vive un volumen.** `docker volume inspect actividad4-mlops_modelos`. ¿Qué
   `Mountpoint` aparece? (En Docker Desktop esa ruta está dentro de la máquina Linux de
   WSL2, no en tu disco de Windows: por eso un volumen con nombre es "irrelevante para el
   usuario".)
7. **Limpieza.** `docker system df`, luego `docker compose down -v --rmi local` y
   `docker system prune`. ¿Cuánto espacio recuperaste?
