# Playlist Player

Importa playlists de YouTube Music y de Spotify pegando su enlace de compartir, las guarda en tu biblioteca local y las reproduce con un clic. No necesita cuenta ni claves de ninguna de las dos plataformas.

Está hecho con Python, PySide6 y VLC, con la misma arquitectura en capas que [ytmusic-client](../ytmusic-client). No está afiliado a YouTube, Google ni Spotify.

## Cómo funciona

1. Pegas un enlace de compartir y pulsas **Importar**.
2. La playlist se guarda en `data/library.json` con su título y todas sus canciones.
3. La eliges en la lista de la izquierda y haces un clic en una canción (o **Reproducir**): suena esa canción y sigue con las siguientes.

Sobre la lista de canciones:

- **Reproducir** empieza desde la primera canción en orden.
- **Aleatorio** reproduce la playlist en orden aleatorio, sin repetir canciones hasta agotarla. El botón queda resaltado mientras el modo está activo; **Reproducir** lo desactiva.
- El botón de bucle de la barra inferior repite la canción actual hasta que lo apagues. Pasar a la siguiente canción con el botón sigue funcionando.
- Los tres puntos de cada playlist (o el clic derecho) abren el menú para eliminarla, con una confirmación.

### Segundo plano y configuración

El engranaje de la esquina superior izquierda abre la configuración, donde cada opción se puede activar o desactivar y se aplica al instante:

- **Seguir en segundo plano:** al cerrar la ventana, la música sigue sonando y la app queda en la bandeja del sistema. Desde el icono de la bandeja puedes abrir la ventana, pausar, cambiar de canción o salir. Si se desactiva, cerrar la ventana cierra la app.
- **Mini reproductor:** cuando minimizas la app o la cierras a la bandeja, aparece una ventana pequeña siempre visible con la canción actual, anterior, pausa, siguiente y un botón para volver a la ventana principal. Se puede arrastrar y recuerda su posición.

Los ajustes se guardan en `data/settings.json`.

Enlaces admitidos:

| Origen | Ejemplos |
|---|---|
| YouTube Music / YouTube | `https://music.youtube.com/playlist?list=...`, `https://www.youtube.com/playlist?list=...`, `.../watch?v=...&list=...`, `.../browse/VL...` |
| Spotify | `https://open.spotify.com/playlist/<id>` (con `?si=` o `/intl-xx/`), `spotify:playlist:<id>`, enlaces cortos `spotify.link/...` |

Solo se importan playlists: no álbumes, canciones sueltas ni artistas de Spotify.

### Detalles a tener en cuenta

- **Spotify no se puede reproducir directamente.** Al importar solo se guarda el título, el artista y la duración. Al reproducir una canción, la app la busca en YouTube Music, elige la coincidencia más parecida (título, artistas y duración) y guarda el resultado, así que la segunda vez ya no necesita buscar. También busca por adelantado las siguientes canciones de la cola. Si no encuentra una coincidencia suficientemente buena, la salta y te avisa.
- **Límite de Spotify:** se lee la vista incrustada pública de la playlist, que trae hasta unas 100 canciones. Las playlists más largas se importan recortadas. Esta vista no es una API oficial y Spotify podría cambiarla; si eso pasa, la app muestra un aviso de que no pudo leerla.
- **Playlists privadas:** no se pueden importar, tienen que ser públicas o estar compartidas por enlace.
- **Volver a importar** una playlist la actualiza y conserva las coincidencias de YouTube ya encontradas.

## Requisitos

- Python 3.10 o superior (probado en 3.14).
- [VLC de 64 bits](https://www.videolan.org/vlc/) instalado. Si ves un error de `libvlc.dll`, casi seguro se mezclan 32 y 64 bits.

## Ejecutar desde el código

```bash
git clone <url-del-repositorio>
cd playlist-player
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python app.py
```

Los datos (biblioteca, ajustes, caché de yt-dlp y registro) se guardan en la carpeta `data/`, que se crea sola y no se versiona.

## Generar el .exe y el instalador

```powershell
pip install pyinstaller pefile
.\build-release.ps1
```

Genera la carpeta `release\PlaylistPlayer\` (con `PlaylistPlayer.exe`) y, si [Inno Setup 6](https://jrsoftware.org/isinfo.php) está instalado (`winget install JRSoftware.InnoSetup`), el instalador `release\PlaylistPlayer-Setup-<versión>.exe`. La versión se lee de `version_info.txt`. El instalador descarga e instala VLC de 64 bits si no lo encuentra.

## Arquitectura

```
app.py            Punto de entrada
core/             config.py (rutas y parámetros), logging_setup.py, bootstrap.py (raíz de composición)
domain/           Modelos, lectura de enlaces, puntuación de coincidencias, caché de streams
infra/            TaskRunner (hilos), fuentes de YouTube Music y Spotify, biblioteca JSON, VLC, yt-dlp
services/         Biblioteca e importación, búsqueda de coincidencias, reproductor, streams
presenters/       Conectan la ventana con los servicios
ui/               Widgets y señales; no conocen los servicios
tests/            Unitarias, de UI y de presenters; test_live_flows.py usa la red real
```

- **Concurrencia:** `TaskRunner` usa un `QThreadPool` y entrega los resultados en el hilo principal. Con `key`, solo llega el último resultado de cada clave.
- **Reproducción:** `PlayerService` mantiene la cola, salta las canciones que fallan (se detiene tras 3 fallos seguidos) y precarga las siguientes; `StreamService` resuelve y cachea las URL de audio con yt-dlp.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Las pruebas normales corren sin red ni pantalla. Las de `tests/test_live_flows.py` importan playlists reales, buscan coincidencias, resuelven un stream y lo reproducen en VLC; se activan con:

```bash
set YTMUSIC_LIVE_TESTS=1 && python -m pytest tests/test_live_flows.py -q -s
```

## Solución de problemas

- **No suena una canción:** yt-dlp depende de YouTube, que cambia con frecuencia. Actualiza con `pip install --upgrade yt-dlp`.
- **Una canción de Spotify suena distinta a la original:** la coincidencia es automática. Si la elegida no es la correcta, elimina y vuelve a importar la playlist, o abre un issue con el caso.
- **Errores en general:** se registran en `data/playlist-player.log`.

## Licencia

[MIT](LICENSE). Usa PySide6 (LGPL), ytmusicapi (MIT), yt-dlp (Unlicense) y VLC (LGPL/GPL, instalado aparte).
