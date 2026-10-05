-- db/init.sql REAL de la Actividad 4 (con explicaciones agregadas, en líneas "-- >")
--
-- > Cómo llega aquí: docker-compose.yml lo monta como bind mount de solo lectura en
-- > /docker-entrypoint-initdb.d/init.sql. La imagen oficial de Postgres ejecuta
-- > todo lo que haya en esa carpeta SOLO cuando inicializa una base vacía.

-- Se ejecuta UNA sola vez: cuando el volumen de Postgres esta vacio.
-- Si el volumen ya tiene datos, Docker ignora este script (y por eso los
-- datos sobreviven a un `docker compose down` sin -v).
-- > Consecuencia: si cambias este archivo, no pasa nada hasta que borres el
-- > volumen pgdata (docker compose down -v), y eso borra el historial.
CREATE TABLE IF NOT EXISTS predicciones (
    id             SERIAL PRIMARY KEY,                  -- > autoincremental: 1, 2, 3...
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),  -- > fecha y hora con zona horaria
    entrada        JSONB       NOT NULL,                -- > el partido recibido, como JSON
    prediccion     TEXT        NOT NULL,                -- > 'Home Win' / 'Away Win' / 'Draw'
    probabilidades JSONB,                               -- > {"Home Win": 0.8764, ...}
    modelo         TEXT                                 -- > p. ej. 'LogisticRegression'
);

-- > Índice para que "ORDER BY creado_en DESC" (las más recientes) sea rápido.
CREATE INDEX IF NOT EXISTS idx_predicciones_creado_en ON predicciones (creado_en DESC);
