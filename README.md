# IAMarker

IAMarker es una herramienta de línea de comandos (CLI) que te permite interactuar con la API de Ollama. Con ella, puedes realizar consultas a modelos de IA instalados localmente y obtener las respuestas en formato Markdown.

## Instalación

Clonar el repositorio e instalar dependencias:

```
git clone https://github.com/Jorge-Marco5/IAMarker.git
cd IAMarker

pip install -r requirements.txt

```

## Configuracion y uso

- ### Comandos de ayuda general

  Para ver lista de acciones dentro del programa

  ```
  python main.py --help
  # ó tambien
  python main.py -h
  ```

  Tambien ayuda de una accion en especifico

  ```
  python main.py <accion> --help
  # Ejemplo
  python main.py change_model --help
  ```

- ### Configurar direccion del servidor

  Por defecto la heramienta se conecta a una direccion local (localhost), si desea cambiar la direccion:

  ```
  python main.py change_server -u <tu ip o host:puerto>
  # Ejemplo
  python main.py change_server -u http://192.168.1.2:11434
  ```

- ### Ver modelos disponibles

  Para ver la lista de modelos disponibles es necesario tener al menos un modelo de IA instalado de forma local en la plataforma de ollama dentro de tu servidor

  ```
  python main.py models
  ```

- ### Cambiar tu modelo de IA

  Cambia el modelo de IA a uno que tengas instalado en la plataforma de ollama dentro de tu servidor

  ```
  python main.py change_model -m <tu-modelo>
  # Ejemplo
  python main.py change_model -m qwen3.5:9b
  ```

- ### Realizar una pregunta rapida al modelo

  Realizar una pregunta rapida al modelo de ia y te retorna una respuesta sin tener una conversacion o guardar contexto

  ```
  python main.py req -t 'tu pregunta'
  # Ejemplo
  python main.py req -t '¿Por que el cielo es azul?'
  ```

  **Incluir un modelo en especifico**

  Puedes usar un modelo especifico diferente al default siempre y cuando esté instalado en tu servidor

  ```
  python main.py req -t 'tu pregunta' -m <tu-otro-modelo>
  # Ejemplo
  python main.py req -t '¿Por que el cielo es azul?' -m <gemma4:12b>
  ```

  - ### Iniciar una conversacion con un modelo de IA

  Inicia una conversacion con un modelo de IA de forma persistente en memoria en el cual el modelo puede trabajar en base a el contexto de la conversacion

  ```
  python main.py chat -t 'tu pregunta'
  # Ejemplo
  python main.py chat -t '¿Por que el cielo es azul?'
  ```

  **Incluir un modelo en especifico**

  Puedes usar un modelo especifico diferente al default siempre y cuando esté instalado en tu servidor, de momento no puedes cambiar el modelo durante la conversacion, solo al iniciar una nueva

  ```
  python main.py chat -t 'tu pregunta' -m <tu-otro-modelo>
  # Ejemplo
  python main.py chat -t '¿Por que el cielo es azul?' -m <gemma4:12b>
  ```

- ### Ver metricas de uso

  Puedes ver estadisticas generales de uso como tokens y tiempo general de uso

  ```
  python main.py metrics -m <tu-modelo>
  # Ejemplo
  python main.py metrics -m <qwen3.5:9b>
  ```
