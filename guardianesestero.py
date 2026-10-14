"""
GUARDIANES DEL ESTERO
Simulador funcional de respuesta comunitaria para proteger un manglar costero.
Requiere Python 3.10+.
Instalacion: python -m pip install ttkbootstrap
Ejecucion: python guardianes_estero.py
"""
from dataclasses import dataclass, replace
from functools import reduce
from typing import Literal
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# ==========================================================
# CAPA DE DATOS: modelos inmutables del simulador
# ==========================================================
@dataclass(frozen=True)
class Brigada:
    id: int
    nombre: str
    especialidad: str
    energia: int
    energia_maxima: int
    impacto: int

@dataclass(frozen=True)
class Orden:
    tipo: Literal["limpiar", "rescatar", "reforestar"]
    brigada_id: int
    zona_id: int

@dataclass(frozen=True)
class ZonaManglar:
    id: int
    nombre: str
    contaminacion: int
    fauna_afectada: int
    plantulas: int
    objetivo_plantulas: int

@dataclass(frozen=True)
class EstadoReserva:
    brigadas: tuple[Brigada, ...]
    zonas: tuple[ZonaManglar, ...]
    bitacora: tuple[str, ...] = ()

ESTADO_BASE = EstadoReserva(
    brigadas=(
        Brigada(1, "Marea Verde", "Limpieza costera", 90, 90, 18),
        Brigada(2, "Raices Vivas", "Restauracion del manglar", 80, 80, 14),
        Brigada(3, "Alas del Estero", "Rescate de fauna", 75, 75, 12),
    ),
    zonas=(
        ZonaManglar(1, "Estero Norte", 68, 7, 12, 35),
        ZonaManglar(2, "Canal de los Cangrejos", 42, 4, 21, 40),
        ZonaManglar(3, "Borde Comunitario", 25, 2, 28, 45),
    )
)

# ==========================================================
# CAPA DE LOGICA: funciones puras
# ==========================================================
def buscar_por_id(elementos, elemento_id):
    """Busca un elemento sin alterar la coleccion original."""
    return next(elemento for elemento in elementos if elemento.id == elemento_id)

def zonas_prioritarias(estado: EstadoReserva):
    """filter identifica zonas con contaminacion alta o fauna afectada."""
    return tuple(filter(lambda z: z.contaminacion >= 40 or z.fauna_afectada >= 4, estado.zonas))

def resumen_zonas(estado: EstadoReserva):
    """map transforma las zonas en lineas breves para el panel de informacion."""
    return tuple(map(
        lambda z: f"{z.nombre}: contaminacion {z.contaminacion}% · fauna afectada {z.fauna_afectada}",
        estado.zonas
    ))

def contaminacion_total(estado: EstadoReserva):
    """reduce suma los indicadores de contaminacion de las zonas."""
    return reduce(lambda total, zona: total + zona.contaminacion, estado.zonas, 0)

def crear_medidor_impacto(multiplicador: float):
    """Closure: conserva el multiplicador elegido para la brigada."""
    def medir(impacto_base: int) -> int:
        return max(1, round(impacto_base * multiplicador))
    return medir

def reemplazar_zona(estado: EstadoReserva, zona_actualizada: ZonaManglar):
    """Devuelve un estado nuevo; no modifica las zonas anteriores."""
    nuevas_zonas = tuple(
        zona_actualizada if zona.id == zona_actualizada.id else zona
        for zona in estado.zonas
    )
    return replace(estado, zonas=nuevas_zonas)

def procesar_orden(estado: EstadoReserva, orden: Orden, medir_impacto):
    """
    Regla pura del dominio. match/case decide que intervencion realizar.
    Devuelve un nuevo estado y una descripcion, sin tocar widgets ni archivos.
    """
    try:
        brigada = buscar_por_id(estado.brigadas, orden.brigada_id)
        zona = buscar_por_id(estado.zonas, orden.zona_id)
    except StopIteration:
        return estado, "No se encontro la brigada o la zona seleccionada."

    if brigada.energia <= 0:
        return estado, f"{brigada.nombre} no tiene energia disponible."

    energia_usada = 8
    impacto = medir_impacto(brigada.impacto)
    match orden.tipo:
        case "limpiar":
            contaminacion = max(0, zona.contaminacion - impacto)
            zona_nueva = replace(zona, contaminacion=contaminacion)
            mensaje = f"♻ {brigada.nombre} retiro residuos en {zona.nombre}. Contaminacion: {contaminacion}%."
        case "rescatar":
            fauna = max(0, zona.fauna_afectada - max(1, impacto // 6))
            zona_nueva = replace(zona, fauna_afectada=fauna)
            mensaje = f"🦀 {brigada.nombre} atendio fauna en {zona.nombre}. Animales aun afectados: {fauna}."
        case "reforestar":
            plantulas = min(zona.objetivo_plantulas, zona.plantulas + impacto)
            zona_nueva = replace(zona, plantulas=plantulas)
            mensaje = f"🌱 {brigada.nombre} sembro en {zona.nombre}. Plantulas: {plantulas}/{zona.objetivo_plantulas}."
        case _:
            return estado, "Tipo de intervencion desconocido."

    brigada_nueva = replace(brigada, energia=max(0, brigada.energia - energia_usada))
    nuevas_brigadas = tuple(brigada_nueva if b.id == brigada.id else b for b in estado.brigadas)
    estado_con_zona = reemplazar_zona(estado, zona_nueva)
    nuevo_estado = replace(
        estado_con_zona,
        brigadas=nuevas_brigadas,
        bitacora=(mensaje,) + estado.bitacora
    )
    return nuevo_estado, mensaje

# Comparacion breve: estilo imperativo con reasignacion local paso a paso.
def calcular_impacto_paso_a_paso(base: int, multiplicador: float):
    resultado = base
    resultado = resultado * multiplicador
    resultado = round(resultado)
    return max(1, resultado)

# ==========================================================
# CAPA VISUAL: los efectos secundarios estan concentrados aqui
# ==========================================================
class GuardianesApp:
    def __init__(self):
        self.root = ttk.Window(themename="darkly")
        self.root.title("Guardianes del Estero | Simulador funcional")
        self.root.geometry("1060x730")
        self.root.minsize(900, 650)
        self.estado = ESTADO_BASE
        self.medir_impacto = crear_medidor_impacto(1.0)
        self.brigada_id = 1
        self.zona_id = 1
        self.crear_interfaz()
        self.actualizar_pantalla()

    def crear_interfaz(self):
        cabecera = ttk.Frame(self.root, padding=(22, 18))
        cabecera.pack(fill=X)
        ttk.Label(cabecera, text="GUARDIANES DEL ESTERO", font=("Segoe UI", 23, "bold"), bootstyle="success").pack(anchor=W)
        ttk.Label(cabecera, text="Centro comunitario de respuesta · Manglares de la costa ecuatoriana", bootstyle="secondary").pack(anchor=W, pady=(3, 0))

        cuerpo = ttk.Frame(self.root, padding=(20, 0, 20, 16))
        cuerpo.pack(fill=BOTH, expand=True)
        cuerpo.columnconfigure(0, weight=3)
        cuerpo.columnconfigure(1, weight=2)
        cuerpo.rowconfigure(1, weight=1)

        self.tarjetas = ttk.Frame(cuerpo)
        self.tarjetas.grid(row=0, column=0, sticky=EW, padx=(0, 14), pady=(0, 12))
        self.tarjetas.columnconfigure((0, 1, 2), weight=1)

        panel = ttk.Labelframe(cuerpo, text=" Centro de operaciones ", padding=14, bootstyle="success")
        panel.grid(row=0, column=1, sticky=EW, pady=(0, 12))
        ttk.Label(panel, text="Brigada asignada").pack(anchor=W)
        self.brigada_var = tk.StringVar(value="Marea Verde")
        self.brigada_combo = ttk.Combobox(panel, textvariable=self.brigada_var, state="readonly",
                                          values=[b.nombre for b in self.estado.brigadas])
        self.brigada_combo.pack(fill=X, pady=(4, 10))
        self.brigada_combo.bind("<<ComboboxSelected>>", self.seleccionar_brigada)

        ttk.Label(panel, text="Zona de intervencion").pack(anchor=W)
        self.zona_var = tk.StringVar(value="Estero Norte")
        self.zona_combo = ttk.Combobox(panel, textvariable=self.zona_var, state="readonly",
                                       values=[z.nombre for z in self.estado.zonas])
        self.zona_combo.pack(fill=X, pady=(4, 10))
        self.zona_combo.bind("<<ComboboxSelected>>", self.seleccionar_zona)

        ttk.Label(panel, text="Nivel de coordinacion").pack(anchor=W)
        self.nivel_var = tk.StringVar(value="Estandar")
        self.nivel_combo = ttk.Combobox(panel, textvariable=self.nivel_var, state="readonly",
                                        values=["Estandar", "Equipo coordinado (+50%)"])
        self.nivel_combo.pack(fill=X, pady=(4, 12))
        self.nivel_combo.bind("<<ComboboxSelected>>", self.cambiar_nivel)

        ttk.Button(panel, text="♻  RETIRAR RESIDUOS", bootstyle="success", command=self.limpiar).pack(fill=X, pady=3)
        ttk.Button(panel, text="🦀  RESCATAR FAUNA", bootstyle="info", command=self.rescatar).pack(fill=X, pady=3)
        ttk.Button(panel, text="🌱  REFORESTAR ZONA", bootstyle="warning", command=self.reforestar).pack(fill=X, pady=3)
        ttk.Button(panel, text="↻  RESTABLECER RESERVA", bootstyle="secondary-outline", command=self.reiniciar).pack(fill=X, pady=(10, 0))

        inferior = ttk.Frame(cuerpo)
        inferior.grid(row=1, column=0, columnspan=2, sticky=NSEW)
        inferior.columnconfigure(0, weight=3)
        inferior.columnconfigure(1, weight=2)
        inferior.rowconfigure(0, weight=1)

        registro = ttk.Labelframe(inferior, text=" Bitacora de intervenciones ", padding=10, bootstyle="secondary")
        registro.grid(row=0, column=0, sticky=NSEW, padx=(0, 14))
        self.log = tk.Text(registro, height=10, wrap="word", font=("Consolas", 10),
                           bg="#10221f", fg="#e5f5ee", relief="flat", padx=10, pady=10)
        self.log.pack(fill=BOTH, expand=True)

        indicadores = ttk.Labelframe(inferior, text=" Indicadores de conservacion ", padding=12, bootstyle="secondary")
        indicadores.grid(row=0, column=1, sticky=NSEW)
        self.contaminacion_label = ttk.Label(indicadores, text="", font=("Segoe UI", 11, "bold"), bootstyle="warning")
        self.contaminacion_label.pack(anchor=W, pady=(0, 8))
        ttk.Label(indicadores, text="Zonas prioritarias", bootstyle="secondary").pack(anchor=W)
        self.prioritarias_label = ttk.Label(indicadores, text="", wraplength=290)
        self.prioritarias_label.pack(anchor=W, pady=(3, 10))
        ttk.Label(indicadores, text="Estado de las zonas (map)", bootstyle="secondary").pack(anchor=W)
        self.resumen_label = ttk.Label(indicadores, text="", justify=LEFT, wraplength=300)
        self.resumen_label.pack(anchor=W, pady=(3, 0))

        ttk.Label(self.root, text="Diseno funcional: estado inmutable · reglas separadas · efectos visuales aislados",
                  anchor=CENTER, bootstyle="secondary", padding=8).pack(fill=X)

    def seleccionar_brigada(self, _event=None):
        self.brigada_id = next(b.id for b in self.estado.brigadas if b.nombre == self.brigada_var.get())

    def seleccionar_zona(self, _event=None):
        self.zona_id = next(z.id for z in self.estado.zonas if z.nombre == self.zona_var.get())

    def cambiar_nivel(self, _event=None):
        factor = 1.5 if self.nivel_var.get().startswith("Equipo coordinado") else 1.0
        self.medir_impacto = crear_medidor_impacto(factor)

    def ejecutar_orden(self, tipo):
        nuevo_estado, mensaje = procesar_orden(
            self.estado, Orden(tipo, self.brigada_id, self.zona_id), self.medir_impacto
        )
        if nuevo_estado == self.estado and mensaje.startswith("No se encontro"):
            messagebox.showerror("Orden no completada", mensaje)
            return
        if nuevo_estado == self.estado and "energia" in mensaje:
            messagebox.showwarning("Energia agotada", mensaje)
            return
        self.estado = nuevo_estado
        self.actualizar_pantalla()

    def limpiar(self):
        self.ejecutar_orden("limpiar")

    def rescatar(self):
        self.ejecutar_orden("rescatar")

    def reforestar(self):
        self.ejecutar_orden("reforestar")

    def reiniciar(self):
        self.estado = ESTADO_BASE
        self.actualizar_pantalla()

    def actualizar_pantalla(self):
        for widget in self.tarjetas.winfo_children():
            widget.destroy()
        for columna, brigada in enumerate(self.estado.brigadas):
            tarjeta = ttk.Labelframe(self.tarjetas, text=f" {brigada.especialidad} ", padding=10, bootstyle="success")
            tarjeta.grid(row=0, column=columna, sticky=NSEW, padx=4)
            ttk.Label(tarjeta, text=brigada.nombre, font=("Segoe UI", 12, "bold")).pack(anchor=W)
            ttk.Label(tarjeta, text=f"Impacto: {brigada.impacto}").pack(anchor=W, pady=(5, 2))
            ttk.Progressbar(tarjeta, maximum=brigada.energia_maxima, value=brigada.energia,
                            bootstyle="success-striped").pack(fill=X, pady=5)
            ttk.Label(tarjeta, text=f"Energia: {brigada.energia}/{brigada.energia_maxima}").pack(anchor=W)

        total = contaminacion_total(self.estado)
        self.contaminacion_label.config(text=f"Contaminacion acumulada: {total}%")
        prioritarias = zonas_prioritarias(self.estado)
        self.prioritarias_label.config(text="\n".join(z.nombre for z in prioritarias) if prioritarias else "Todas las zonas bajo control")
        self.resumen_label.config(text="\n".join(resumen_zonas(self.estado)))
        self.log.delete("1.0", END)
        self.log.insert("1.0", "\n".join(self.estado.bitacora) if self.estado.bitacora else
                        "Reserva lista. Elige una brigada, una zona y una intervencion.")

    def ejecutar(self):
        self.root.mainloop()

if __name__ == "__main__":
    GuardianesApp().ejecutar()
