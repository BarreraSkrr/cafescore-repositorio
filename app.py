"""ZONA LIBRE: la interfaz de la aplicación de CaféScore para Cereza Café.

Para verla en su computador:   streamlit run app.py"""
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from core import (cargar_config, cargar_metadata, cargar_modelo, cargar_resultados, etiqueta, evaluar,
                  hay_modelo, texto_razon, validar)

config = cargar_config()
st.set_page_config(page_title=config["titulo"], page_icon="☕", layout="wide")

col_logo, col_titulo = st.columns([1, 8])
with col_logo:
    try:
        st.image(config["logo"], width=90)
    except Exception:
        st.markdown("# ☕")
with col_titulo:
    st.title(config["titulo"])
    st.caption(f"{config['cliente']} · {config['descripcion']}")

if not hay_modelo():
    st.info("Todavía no hay modelo en la carpeta model/. Sigan la guía del README.")
    st.divider()
    st.caption(config["pie"])
    st.stop()


TIENDAS = pd.DataFrame({"tienda": ["Chapinero", "Teusaquillo", "Usaquén"],
                        "lat": [4.6486, 4.6318, 4.6950], "lon": [-74.0628, -74.0726, -74.0306]})
CLASES = ["oportunidad", "en equilibrio", "saturada", "sin demanda"]
COLORES = {"oportunidad": [46, 125, 50], "en equilibrio": [249, 168, 37], "saturada": [198, 40, 40],
           "sin demanda": [189, 189, 189]}
DEFINICIONES = {
    "oportunidad": "El perfil de la zona se parece al de las zonas con café y le falta al menos un café frente a lo que el modelo espera. Estudiar y buscar local.",
    "en equilibrio": "Tiene demanda y los cafés que su perfil sostiene. Abrir solo con un concepto distinto al de los cafés que ya están.",
    "saturada": "Tiene al menos un café más de los que su perfil sostiene. No abrir: los cafés de hoy ya se reparten la demanda.",
    "sin demanda": "El puntaje está por debajo del umbral: el perfil no se parece al de las zonas con café. No estudiar.",
}
ACCIONES = {
    "Centro de negocios": "Primer lugar para buscar local. Tienda de oficina y universidad: barra rápida en la mañana, mesas para trabajar en la tarde.",
    "Corredor comercial": "Segundo lugar para buscar local, cerca de TransMilenio. Tienda de paso: café para llevar y precio de entrada.",
    "Residencial con parques y colegios": "No buscar local por ahora. Si se abre, café de barrio para fines de semana y venta de grano.",
    "Residencial popular": "No buscar local. Llegar con venta de grano en tiendas de barrio.",
    "Periferia sin actividad": "Descartar: casi no hay negocios ni gente que pase.",
}


@st.cache_resource
def recursos():
    return cargar_metadata(), cargar_modelo(), cargar_resultados()


meta, modelo, resultados = recursos()
resultados = resultados.copy()
m = meta["metricas"]
col_id = meta["columna_id"]
evento = meta["evento"]


def distancia_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = np.radians(lat1), np.radians(lon1), np.radians(lat2), np.radians(lon2)
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * np.arcsin(np.sqrt(a))


def millones(valor, decimales=1):
    return f"{valor:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def entero(valor):
    return f"{valor:,.0f}".replace(",", ".")


def chip(clase):
    r, g, b = COLORES[clase]
    return (f"<span style='background:rgb({r},{g},{b});color:white;padding:3px 12px;border-radius:999px;"
            f"font-weight:600'>{clase}</span>")


with st.sidebar:
    st.header("Filtros")
    arriendo_max = st.slider("Arriendo máximo (millones al mes, local de 80 m²)", 2.0, 20.0,
                             float(m.get("arriendo_maximo", 12)), 0.5)
    radio = st.slider("Distancia mínima a las tiendas actuales (m)", 0, 3000,
                      int(m.get("radio_canibalizacion", 1000)), 100)
    clases_vistas = st.multiselect("Clases en el mapa", CLASES, default=CLASES)
    st.caption("El arriendo se estima con el valor del suelo: en Chapinero Central un local de 80 m² cuesta "
               "en promedio 6,5 millones al mes (Fincaraíz, 2026). Una tienda nueva a menos de la distancia "
               "mínima le quitaría clientes a una actual.")

resultados["pasa_filtros"] = (resultados["arriendo_estimado"] <= arriendo_max) & (resultados["dist_tienda_m"] >= radio)


def mejores(tabla, cuantas=10):
    candidatas = tabla[(tabla["clase"] == "oportunidad") & tabla["pasa_filtros"]]
    candidatas = candidatas.sort_values(["brecha", "probabilidad"], ascending=False)
    elegidas = []
    separacion = m.get("separacion_minima", 500)
    for i, fila in candidatas.iterrows():
        if all(distancia_m(fila["lat"], fila["lon"], tabla.loc[j, "lat"], tabla.loc[j, "lon"]) >= separacion for j in elegidas):
            elegidas.append(i)
        if len(elegidas) == cuantas:
            break
    salida = tabla.loc[elegidas].copy()
    salida.insert(0, "puesto", range(1, len(salida) + 1))
    return salida


def capa_tiendas():
    tiendas = TIENDAS.copy()
    tiendas["texto"] = "Tienda de Cereza en " + tiendas["tienda"]
    return pdk.Layer("ScatterplotLayer", data=tiendas, id="tiendas", get_position="[lon, lat]",
                     get_fill_color=[20, 20, 20], get_line_color=[255, 255, 255], line_width_min_pixels=2,
                     stroked=True, get_radius=220, pickable=True)


def mapa(tabla, clave, seleccionable=True, zoom=11, numeros=False):
    datos = tabla.copy()
    datos["color"] = [COLORES[c] + ([210] if p else [70]) for c, p in zip(datos["clase"], datos["pasa_filtros"])]
    datos["texto"] = ("Zona " + datos[col_id].astype(str) + "<br>Clase: " + datos["clase"]
                      + "<br>Puntaje: " + (datos["probabilidad"] * 100).round(0).astype(int).astype(str) + " %"
                      + "<br>Cafés hoy: " + datos["n_cafes"].astype(str)
                      + " · esperados: " + datos["cafes_esperados"].round(1).astype(str)
                      + "<br>Arriendo estimado: " + datos["arriendo_estimado"].astype(str) + " M/mes"
                      + "<br>A " + datos["dist_tienda_m"].astype(int).astype(str) + " m de la tienda de " + datos["tienda_cercana"])
    zonas = pdk.Layer("H3HexagonLayer", data=datos, id="zonas", get_hexagon=col_id, get_fill_color="color",
                      stroked=False, extruded=False, pickable=True, auto_highlight=True)
    vista = pdk.ViewState(latitude=float(datos["lat"].mean()), longitude=float(datos["lon"].mean()), zoom=zoom)
    capas = [zonas, capa_tiendas()]
    if numeros:
        capas.append(pdk.Layer("TextLayer", data=datos, id="numeros", get_position="[lon, lat]", get_text="puesto_texto",
                               get_size=18, get_color=[0, 0, 0], get_pixel_offset=[0, -18]))
    deck = pdk.Deck(layers=capas, initial_view_state=vista, map_style=None,
                    tooltip={"html": "{texto}"})
    if seleccionable:
        return st.pydeck_chart(deck, on_select="rerun", selection_mode="single-object", key=clave, height=560)
    return st.pydeck_chart(deck, key=clave, height=420)


def ficha_zona(fila, lat_punto=None, lon_punto=None):
    if lat_punto is None:
        lat_punto, lon_punto = float(fila["lat"]), float(fila["lon"])
    st.markdown(f"#### Zona {fila[col_id]} &nbsp; {chip(fila['clase'])}", unsafe_allow_html=True)
    st.caption(DEFINICIONES[fila["clase"]])
    c1, c2, c3 = st.columns(3)
    c1.metric("Puntaje (probabilidad de tener café)", f"{fila['probabilidad']:.0%}")
    c2.metric("Cafés hoy / esperados", f"{int(fila['n_cafes'])} / {millones(fila['cafes_esperados'])}")
    c3.metric("Arriendo estimado", f"{millones(fila['arriendo_estimado'])} M/mes")
    st.markdown(f"**Recomendación del modelo:** {fila['decision'].lower()}.")
    st.markdown(f"**Tipo de zona:** {fila['segmento']}. {ACCIONES.get(fila['segmento'], '')}")
    st.markdown(f"**Valor del suelo:** {millones(fila['valor_suelo_millones'], 2)} millones por m²")
    razones = [r for r in str(fila.get("razones", "")).split(" · ") if r and r != "nan"]
    if razones:
        st.markdown("**Razones principales del puntaje**")
        for r in razones:
            st.markdown(f"- {r.replace(' pts', ' puntos de probabilidad')}")
        st.caption("Cuánto cambia el puntaje si esa variable tuviera el valor típico de la ciudad. Muestra de qué "
                   "depende el modelo, no qué pasaría si la zona cambiara.")
    distancias = TIENDAS.copy()
    distancias["Distancia (m)"] = distancia_m(lat_punto, lon_punto, distancias["lat"], distancias["lon"]).round().astype(int)
    distancias["¿Le quitaría clientes?"] = np.where(distancias["Distancia (m)"] < radio, "sí, está muy cerca", "no")
    st.markdown("**Distancia a las tiendas actuales de Cereza**")
    st.dataframe(distancias[["tienda", "Distancia (m)", "¿Le quitaría clientes?"]].rename(columns={"tienda": "Tienda"}),
                 hide_index=True, width="stretch")


def vista_mapa():
    st.subheader("Mapa de oportunidades de Bogotá")
    st.caption("Cada hexágono es una zona de unos 0,1 km². Los colores pálidos no cumplen el arriendo o la distancia "
               "de los filtros. Los puntos negros son las tiendas actuales. Hagan clic en una zona para ver su ficha.")
    conteo = resultados["clase"].value_counts()
    columnas = st.columns(4)
    for col, clase in zip(columnas, CLASES):
        col.markdown(f"{chip(clase)} &nbsp; **{entero(conteo.get(clase, 0))}** zonas", unsafe_allow_html=True)
    evento_mapa = mapa(resultados[resultados["clase"].isin(clases_vistas)], "mapa_principal")
    try:
        objetos = evento_mapa.selection["objects"].get("zonas", [])
    except Exception:
        objetos = []
    if objetos:
        elegida = resultados[resultados[col_id].astype(str) == str(objetos[0][col_id])]
        if len(elegida):
            st.divider()
            ficha_zona(elegida.iloc[0])


def vista_consulta():
    st.subheader("Consultar una zona o una ubicación")
    modo = st.radio("¿Cómo quieren buscar?", ["Escribir coordenadas", "Elegir una de las 10 mejores"], horizontal=True)
    if modo == "Escribir coordenadas":
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitud", value=4.6486, format="%.5f", step=0.001)
        lon = c2.number_input("Longitud", value=-74.0628, format="%.5f", step=0.001)
        st.caption("Pueden copiar las coordenadas de Google Maps (clic derecho sobre el punto).")
        distancias = distancia_m(lat, lon, resultados["lat"], resultados["lon"])
        cercana = int(np.argmin(distancias))
        if distancias[cercana] > 400:
            st.warning(f"Ese punto está a {entero(distancias[cercana])} m de la zona analizada más cercana: "
                       "puede estar fuera de Bogotá urbana. Se muestra esa zona.")
        ficha_zona(resultados.iloc[cercana], lat, lon)
    else:
        top = mejores(resultados)
        if top.empty:
            st.info("Con estos filtros no queda ninguna zona de oportunidad.")
            return
        opcion = st.selectbox("Zona", [f"{p}. Zona {z}" for p, z in zip(top["puesto"], top[col_id])])
        ficha_zona(top.iloc[int(opcion.split(".")[0]) - 1])


def vista_mejores():
    st.subheader("Las 10 mejores zonas para buscar local")
    st.caption(f"Zonas de oportunidad con arriendo estimado de hasta {millones(arriendo_max)} millones al mes y a más de "
               f"{entero(radio)} m de las tiendas, ordenadas por cuántos cafés les faltan (brecha) y luego por puntaje. "
               f"Dos zonas de la lista están a más de {entero(m.get('separacion_minima', 500))} m entre sí.")
    top = mejores(resultados)
    if top.empty:
        st.info("Con estos filtros no queda ninguna zona de oportunidad. Suban el arriendo o bajen la distancia.")
        return
    margen = m.get("margen_tienda", 15)
    tabla = pd.DataFrame({
        "Puesto": top["puesto"], "Zona": top[col_id], "Tipo de zona": top["segmento"],
        "Puntaje": (top["probabilidad"] * 100).round(0).astype(int).astype(str) + " %",
        "Cafés hoy": top["n_cafes"], "Cafés esperados": top["cafes_esperados"].round(1),
        "Valor del suelo (M/m²)": top["valor_suelo_millones"], "Arriendo estimado (M/mes)": top["arriendo_estimado"],
        "Margen después del arriendo (M/mes)": (margen - top["arriendo_estimado"]).round(1),
        "Distancia a la tienda más cercana (m)": top["dist_tienda_m"].astype(int),
        "Tienda más cercana": top["tienda_cercana"], "Razones": top["razones"],
        "Latitud": top["lat"].round(5), "Longitud": top["lon"].round(5),
    })
    st.dataframe(tabla, hide_index=True, width="stretch")
    st.download_button("Descargar la lista (CSV)", tabla.to_csv(index=False).encode("utf-8-sig"),
                       "cafescore_10_mejores.csv", "text/csv")
    top["puesto_texto"] = top["puesto"].astype(str)
    mapa(top, "mapa_top", seleccionable=False, zoom=11.3, numeros=True)
    st.caption(f"Margen de una tienda que funciona antes de arriendo: unos {margen} millones al mes (brief del caso).")


def vista_valor():
    st.subheader("¿Cuánto vale el mapa frente a la regla simple?")
    st.markdown(f"**Regla simple:** {m['regla_simple']}. Se compara en las {m['zonas_prueba']} zonas de prueba "
                f"({m['zonas_prueba_con_cafe']} con café), que el modelo no vio al entrenarse.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Costo de los errores con el modelo", f"{entero(m['costo_modelo'])} M", help=f"Modelo: {m['modelo'].lower()}")
    c2.metric("Costo de los errores con la regla", f"{entero(m['costo_regla'])} M")
    a, b = m["intervalo_diferencia"]
    c3.metric("Ahorro frente a la regla", f"{entero(m['costo_regla'] - m['costo_modelo'])} M",
              help=f"Intervalo de 95 %: de {entero(a)} a {entero(b)} millones")
    st.caption(f"Costos {m['unidad_costo']}. Intervalo de 95 % del ahorro: de {entero(a)} a {entero(b)} millones "
               "(1.000 remuestreos de bloques de prueba).")
    if a <= 0 <= b:
        st.warning("El intervalo del ahorro incluye el cero: con estos datos **no se puede afirmar que el modelo le gane "
                   "a la regla** para escoger qué zonas estudiar. Los modelos más potentes (bosque aleatorio y XGBoost) "
                   "tampoco se separaron de la regla.")
    if "tabla_modelos" in m:
        st.markdown("**Todos los modelos en las zonas de prueba**")
        st.dataframe(pd.DataFrame(m["tabla_modelos"]), hide_index=True, width="stretch")
    st.markdown("**Con el presupuesto de estudios** (como en el ejemplo del brief)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Estudios para encontrar 2 zonas aptas con la regla", millones(m["estudios_2_aptas_regla"]))
    c2.metric("Con el modelo", millones(m["estudios_2_aptas_modelo"]))
    c3.metric("Ahorro en estudios (20 M cada uno)", f"{entero(m['ahorro_estudios'])} M",
              help=f"Intervalo de 95 %: {entero(m['intervalo_ahorro_estudios'][0])} a {entero(m['intervalo_ahorro_estudios'][1])} M")
    st.caption("Supuesto: una zona es apta si hoy sostiene al menos un café. Intervalo de 95 % del ahorro: de "
               f"{entero(m['intervalo_ahorro_estudios'][0])} a {entero(m['intervalo_ahorro_estudios'][1])} millones.")
    if "regla_estudia_por_clase" in m:
        st.markdown("**Lo que la regla no ve**")
        estudia = m["regla_estudia_por_clase"]
        total = sum(estudia.values())
        st.markdown(f"La regla manda a estudiar {entero(total)} zonas de la ciudad y las trata a todas igual. El mapa las "
                    f"separa: {entero(estudia['oportunidad'])} son oportunidad, {entero(estudia['en equilibrio'])} están en "
                    f"equilibrio, {entero(estudia['saturada'])} están saturadas y {entero(estudia['sin demanda'])} no tienen "
                    "el perfil de demanda. Además el mapa filtra por arriendo y por distancia a las tiendas y explica cada zona.")
    st.info("Una buena ubicación no garantiza que un café funcione: el local, el concepto y la operación siguen "
            "decidiendo, y el estudio de la zona sigue siendo necesario.")


def vista_simular():
    st.subheader("Simular una zona")
    st.caption("Para la analista de crédito: escriban los datos de una zona (por ejemplo, después de visitarla) y vean "
               "el puntaje del modelo con sus razones. Los valores por defecto son los de una zona típica de Bogotá.")
    valores = {}
    with st.form("nuevo"):
        columnas = st.columns(3)
        for i, col in enumerate(meta["columnas"]):
            with columnas[i % 3]:
                valores[col["nombre"]] = st.number_input(etiqueta(meta, col["nombre"]), value=float(col["referencia"]),
                                                         key="sim_" + col["nombre"])
        enviado = st.form_submit_button("Calcular puntaje")
    if enviado:
        datos, errores, avisos = validar(pd.DataFrame([valores]), meta)
        for e in errores:
            st.error(e)
        for a in avisos:
            st.warning(a)
        if not errores:
            r = evaluar(modelo, meta, datos)[0]
            c1, c2 = st.columns(2)
            c1.metric(f"Probabilidad de {evento}", f"{r['probabilidad']:.0%}")
            c2.metric("Recomendación", r["decision"])
            for razon in r["razones"]:
                st.markdown(f"- {texto_razon(razon, meta)}")


def vista_como_decide():
    st.subheader("Cómo decide el mapa")
    limites = [0.0] + meta["umbrales"] + [1.0]
    st.table(pd.DataFrame({"Puntaje": [f"{limites[i]:.0%} a {limites[i + 1]:.0%}" for i in range(len(meta["decisiones"]))],
                           "Recomendación": meta["decisiones"]}))
    st.caption(f"El umbral sale de minimizar el costo de los errores (60 M por zona con café descartada, 20 M por zona "
               f"sin café estudiada) con validación cruzada por bloques de ciudad. Modelo: {m['modelo'].lower()}.")
    st.markdown("**Las cuatro clases**")
    for clase in CLASES:
        st.markdown(f"{chip(clase)} &nbsp; {DEFINICIONES[clase]}", unsafe_allow_html=True)
    st.caption("Los cafés esperados vienen de un modelo del número de cafés; la brecha es esperados menos cafés de hoy. "
               "El puntaje de cada zona viene de un modelo que no vio su bloque de ciudad.")
    st.markdown("**Tipos de zona (segmentación) y acción para Cereza**")
    tipos = resultados.groupby("segmento").agg(zonas=(col_id, "size"), con_cafe=("n_cafes", lambda s: (s > 0).mean()))
    tipos = tipos.reindex([s for s in ACCIONES if s in tipos.index])
    st.table(pd.DataFrame({"Tipo de zona": tipos.index, "Zonas": tipos["zonas"].values,
                           "% con café": (tipos["con_cafe"] * 100).round(0).astype(int).values,
                           "Acción": [ACCIONES[s] for s in tipos.index]}).set_index("Tipo de zona"))
    st.caption(f"Modelo entrenado con {entero(meta['n_entrenamiento'])} zonas; exportado el {meta['fecha_exportacion']}.")


pestanas = st.tabs(["Mapa", "Consultar una zona", "Las 10 mejores", "Cuánto vale el mapa", "Simular una zona", "Cómo decide"])
with pestanas[0]:
    vista_mapa()
with pestanas[1]:
    vista_consulta()
with pestanas[2]:
    vista_mejores()
with pestanas[3]:
    vista_valor()
with pestanas[4]:
    vista_simular()
with pestanas[5]:
    vista_como_decide()

st.divider()
st.caption(config["pie"])
