# CaféScore · mapa de oportunidades para Cereza Café

Aplicación web que le muestra a Cereza Café en qué zonas de Bogotá vale la pena estudiar un local para sus dos tiendas nuevas de 2027.

Proyecto final de Minería de Datos (ADMI 2559), Universidad de los Andes, 2026-2.
Equipo: Tomás Barrera, Valentina Hernández, María Paz Luna y María Lucía Rincón.

## Qué hace la aplicación

- **Mapa**: las 3.275 zonas de la ciudad con su puntaje (probabilidad de tener café según su perfil) y su clase: oportunidad, en equilibrio, saturada o sin demanda.
- **Consultar una zona**: con unas coordenadas o desde el mapa, muestra el puntaje, la clase, las razones principales y la distancia a las tres tiendas actuales.
- **Las 10 mejores**: zonas de oportunidad filtradas por el arriendo que Cereza puede pagar y por la distancia a sus tiendas.
- **Cuánto vale el mapa**: el modelo frente a la regla simple en las zonas de prueba, con intervalos de confianza.
- **Simular una zona** y **Cómo decide**: el puntaje de una zona escrita a mano, las definiciones de las clases y los tipos de zona.

## Qué hay en el repositorio

| Archivo o carpeta | Qué es |
|---|---|
| `app.py`, `mi_app.py` | La interfaz (zona libre de la plantilla del curso) |
| `core/`, `exportar.py`, `desplegar.py`, `check.py`, `web/` | La zona fija de la plantilla del curso, sin cambios |
| `model/pipeline.joblib` | El modelo final: regresión logística con su preparación de datos |
| `model/metadata.json` | Variables, umbral, decisiones y métricas en las zonas de prueba |
| `model/resultados.csv` | Resultados por zona: puntaje fuera de bloque, clase, cafés esperados, arriendo estimado y distancias |
| `model/ejemplo_entrada.csv` | Tres filas inventadas con valores típicos para probar el modelo |
| `CafeScore_Entrega_Final.ipynb` | El cuaderno con la segunda vuelta de CRISP-DM, el despliegue y la exportación |
| `requirements.txt` | Versiones exactas de las librerías |

## Datos

Este repositorio **no lleva los datos originales del curso** (`cafescore_data.csv`), por las condiciones de uso de la universidad. Solo lleva el modelo y la tabla de resultados que la aplicación necesita.

Para correr el cuaderno: abrirlo en Google Colab, subir `cafescore_data.csv` (descargado de Bloque Neón) y, para exportar la aplicación, `plantilla_app.zip`. Después, ejecutar todo.

## Correr la aplicación en un computador

```
pip install -r requirements.txt
python check.py
streamlit run app.py
```

`check.py` debe terminar en `LISTO PARA DESPLEGAR`. La aplicación publicada corre en Streamlit Community Cloud (archivo principal `app.py`, Python 3.13).

## Fuentes y licencias

© colaboradores de OpenStreetMap (ODbL) · Overture Maps (CDLA-Permissive 2.0) · Foursquare OS Places (Apache 2.0) · datos abiertos del Catastro de Bogotá y de TransMilenio. Cereza Café es una marca ficticia creada para el curso.
