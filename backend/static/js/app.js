// =============================================================================
// app.js — Frontend Pomodoro por pantallas
// =============================================================================

// -----------------------------------------------------------------------------
// Estado global
// -----------------------------------------------------------------------------

const tareas = [];

let tareaSeleccionada = null;
let minutosTrabajo = 25;
let minutosDescanso = 5;
let actividadesDescansoSugeridas = [];

let intervalStatus = null;


// -----------------------------------------------------------------------------
// Helper DOM
// -----------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);


// -----------------------------------------------------------------------------
// Pantallas
// -----------------------------------------------------------------------------

const pantallaTareas = $("pantalla-tareas");
const pantallaPropuesta = $("pantalla-propuesta");
const pantallaEjecucion = $("pantalla-ejecucion");
const pantallaFinal = $("pantalla-final");


function mostrarPantalla(nombre) {
    const pantallas = document.querySelectorAll(".pantalla");

    pantallas.forEach((pantalla) => {
        pantalla.classList.add("oculto");
    });

    const pantallaActiva = document.getElementById(`pantalla-${nombre}`);

    if (pantallaActiva) {
        pantallaActiva.classList.remove("oculto");
    }
}


// -----------------------------------------------------------------------------
// Referencias DOM
// -----------------------------------------------------------------------------

// Formulario tareas
const formTarea = $("form-tarea");
const inputNombre = $("input-nombre");
const inputDificultad = $("input-dificultad");
const valorDificultad = $("valor-dificultad");
const inputConcentracion = $("input-concentracion");
const valorConcentracion = $("valor-concentracion");
const selectDia = $("select-dia");
const selectMes = $("select-mes");
const selectAnio = $("select-anio");

// Eventos de slider
if (inputDificultad && valorDificultad) {
    inputDificultad.addEventListener("input", (e) => {
        valorDificultad.textContent = e.target.value;
    });
}
if (inputConcentracion && valorConcentracion) {
    inputConcentracion.addEventListener("input", (e) => {
        valorConcentracion.textContent = e.target.value;
    });
}

// Lista tareas
const mensajeVacio = $("mensaje-vacio");
const listaTareasEl = $("lista-tareas");
const btnGenerarPropuesta = $("btn-generar-propuesta");

// Propuesta
const propuestaTarea = $("propuesta-tarea");
const propuestaDificultad = $("propuesta-dificultad");
const propuestaConcentracion = $("propuesta-concentracion");
const propuestaPuntaje = $("propuesta-puntaje");
const propuestaTrabajo = $("propuesta-trabajo");
const propuestaDescanso = $("propuesta-descanso");
const propuestaMensaje = $("propuesta-mensaje");

const btnAceptarPropuesta = $("btn-aceptar-propuesta");
const btnAjustarManual = $("btn-ajustar-manual");
const btnVolverTareas = $("btn-volver-tareas");

const bloqueAjuste = $("bloque-ajuste");
const inputTrabajoManual = $("input-trabajo-manual");
const inputDescansoManual = $("input-descanso-manual");
const btnIniciarManual = $("btn-iniciar-manual");

// Ejecución
const execModo = $("exec-modo");
const execTarea = $("exec-tarea");
const execTiempo = $("exec-tiempo");

const btnIniciar = $("btn-iniciar");
const btnPausar = $("btn-pausar");
const btnReanudar = $("btn-reanudar");
const btnFinalizar = $("btn-finalizar");
const btnVolverDesdeEjecucion = $("btn-volver-desde-ejecucion");

// Final
const btnFinalVolverTareas = $("btn-final-volver-tareas");
const btnContinuarBloque = $("btn-continuar-bloque");
const btnMarcarTerminada = $("btn-marcar-terminada");


// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

function nuevoId() {
    return "t_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
}

function formatearSegundos(seg) {
    seg = Math.max(0, parseInt(seg, 10) || 0);

    const m = Math.floor(seg / 60);
    const s = seg % 60;

    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
}

function escaparHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
}


// -----------------------------------------------------------------------------
// Render tareas
// -----------------------------------------------------------------------------

function renderListaTareas() {
    listaTareasEl.innerHTML = "";

    if (tareas.length === 0) {
        mensajeVacio.classList.remove("oculto");
        btnGenerarPropuesta.disabled = true;
        return;
    }

    mensajeVacio.classList.add("oculto");
    
    // El botón solo se habilita si hay al menos una tarea pendiente
    const tienePendientes = tareas.some((t) => !t.terminada);
    btnGenerarPropuesta.disabled = !tienePendientes;

    tareas.forEach((t) => {
        const li = document.createElement("li");
        li.className = "tarea-item";

        if (t.terminada) {
            li.classList.add("terminada");
        } else if (tareaSeleccionada && tareaSeleccionada.id === t.id) {
            li.classList.add("seleccionada");
        }

        // Crear checkbox interactivo
        const chk = document.createElement("input");
        chk.type = "checkbox";
        chk.className = "tarea-checkbox";
        chk.checked = t.terminada;
        chk.addEventListener("change", () => {
            toggleTerminada(t.id);
        });

        const info = document.createElement("div");
        info.className = "tarea-info";

        let metaHtml = `Dificultad: ${t.dificultad} · Concentración: ${t.concentracion}`;
        if (t.fechaEntrega) {
            metaHtml += ` · Vence: ${t.fechaEntrega}`;
        }

        info.innerHTML = `
            <div class="tarea-nombre">${escaparHtml(t.nombre)}</div>
            <div class="tarea-meta">
                ${metaHtml}
            </div>
        `;

        // Solo permitir seleccionar si no está completada
        if (!t.terminada) {
            info.addEventListener("click", () => {
                seleccionarTareaManual(t.id);
            });
        }

        const btnDel = document.createElement("button");
        btnDel.className = "btn-eliminar";
        btnDel.textContent = "Eliminar";

        btnDel.addEventListener("click", () => {
            eliminarTarea(t.id);
        });

        li.appendChild(chk);
        li.appendChild(info);
        li.appendChild(btnDel);

        listaTareasEl.appendChild(li);
    });

    actualizarProgreso();
}

function toggleTerminada(id) {
    const t = tareas.find((x) => x.id === id);
    if (!t) return;

    t.terminada = !t.terminada;

    // Si se marca como terminada y estaba seleccionada, deseleccionarla
    if (t.terminada && tareaSeleccionada && tareaSeleccionada.id === id) {
        tareaSeleccionada = null;
        btnIniciar.disabled = true;
    }

    renderListaTareas();
}

function actualizarProgreso() {
    const contenedor = $("contenedor-progreso");
    const relleno = $("barra-progreso-relleno");
    const porcentajeEl = $("progreso-porcentaje");

    if (!contenedor || !relleno || !porcentajeEl) return;

    if (tareas.length === 0) {
        contenedor.classList.add("oculto");
        return;
    }

    contenedor.classList.remove("oculto");
    const terminadas = tareas.filter((t) => t.terminada).length;
    const porcentaje = Math.round((terminadas / tareas.length) * 100) || 0;

    relleno.style.width = porcentaje + "%";
    porcentajeEl.textContent = porcentaje + "%";
}


// -----------------------------------------------------------------------------
// Crear tarea
// -----------------------------------------------------------------------------

formTarea.addEventListener("submit", (ev) => {
    ev.preventDefault();

    const nombre = inputNombre.value.trim();
    const dificultad = parseInt(inputDificultad.value, 10);
    const concentracion = parseInt(inputConcentracion.value, 10);
    
    const dia = selectDia ? selectDia.value : "";
    const mes = selectMes ? selectMes.value : "";
    const anio = selectAnio ? selectAnio.value : "";
    
    if (!dia || !mes || !anio) {
        alert("La fecha de entrega es obligatoria. Por favor selecciona el Día, Mes y Año.");
        return;
    }
    
    const fechaEntrega = `${anio}-${mes}-${dia}`;
    
    // Validar que no sea del pasado
    const partes = fechaEntrega.split("-");
    const entrega = new Date(parseInt(partes[0], 10), parseInt(partes[1], 10) - 1, parseInt(partes[2], 10));
    const hoy = new Date();
    entrega.setHours(0, 0, 0, 0);
    hoy.setHours(0, 0, 0, 0);
    
    if (entrega < hoy) {
        alert("La fecha de entrega no puede ser anterior a hoy.");
        return;
    }

    if (!nombre) return;
    if (isNaN(dificultad) || dificultad < 1 || dificultad > 5) return;
    if (isNaN(concentracion) || concentracion < 1 || concentracion > 5) return;

    tareas.push({
        id: nuevoId(),
        nombre,
        dificultad,
        concentracion,
        fechaEntrega,
        terminada: false, // Por defecto inicia pendiente
    });

    formTarea.reset();
    inputDificultad.value = 3;
    if (valorDificultad) valorDificultad.textContent = "3";
    inputConcentracion.value = 3;
    if (valorConcentracion) valorConcentracion.textContent = "3";

    renderListaTareas();
});


// -----------------------------------------------------------------------------
// Eliminar tarea
// -----------------------------------------------------------------------------

function eliminarTarea(id) {
    const idx = tareas.findIndex((t) => t.id === id);

    if (idx === -1) return;

    tareas.splice(idx, 1);

    if (tareaSeleccionada && tareaSeleccionada.id === id) {
        tareaSeleccionada = null;
        btnIniciar.disabled = true;
    }

    renderListaTareas();
}


// -----------------------------------------------------------------------------
// Seleccionar tarea manualmente
// -----------------------------------------------------------------------------

function seleccionarTareaManual(id) {
    const t = tareas.find((x) => x.id === id);

    if (!t) return;

    tareaSeleccionada = t;
    minutosTrabajo = 25;
    minutosDescanso = 5;

    btnIniciar.disabled = false;

    renderListaTareas();
}


// -----------------------------------------------------------------------------
// Propuesta con Agente IA (Llama) + fallback local de red
// -----------------------------------------------------------------------------

/**
 * Fallback solo para cuando fetch() falla (sin red).
 * El backend ya tiene su propio fallback para errores de Llama.
 */
function calcularPuntajePrioridadLocal(t) {
    const dif = parseInt(t.dificultad, 10) || 3;
    const con = parseInt(t.concentracion, 10) || 3;
    const base = dif + con;
    
    if (!t.fechaEntrega) return base;
    
    const partes = t.fechaEntrega.split("-");
    if (partes.length !== 3) return base;
    
    const entrega = new Date(parseInt(partes[0], 10), parseInt(partes[1], 10) - 1, parseInt(partes[2], 10));
    const hoy = new Date();
    entrega.setHours(0, 0, 0, 0);
    hoy.setHours(0, 0, 0, 0);
    
    const diffTime = entrega.getTime() - hoy.getTime();
    const dias = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    let bonus = 0;
    if (dias <= 0) {
        bonus = 20 - dias; // Vence hoy o vencida: máxima prioridad absoluta!
    } else if (dias <= 7) {
        bonus = (8 - dias) * 2;
    } else if (dias <= 15) {
        bonus = 15 - dias;
    }
    
    return base + bonus;
}

function calcularPropuestaLocal(listaTareas) {
    if (listaTareas.length === 0) return null;

    const conPuntaje = listaTareas.map((t) => {
        const puntaje = calcularPuntajePrioridadLocal(t);
        let razon = "Prioridad base según dificultad y concentración.";
        
        if (t.fechaEntrega) {
            const partes = t.fechaEntrega.split("-");
            const entrega = new Date(parseInt(partes[0], 10), parseInt(partes[1], 10) - 1, parseInt(partes[2], 10));
            const hoy = new Date();
            entrega.setHours(0, 0, 0, 0);
            hoy.setHours(0, 0, 0, 0);
            const dias = Math.ceil((entrega.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
            
            if (dias <= 0) {
                razon = `⚠️ VENCIDA O PARA HOY (${t.fechaEntrega}). ¡Atención crítica urgente!`;
            } else if (dias <= 3) {
                razon = `Vence muy pronto en ${dias} días (${t.fechaEntrega}). Prioridad alta.`;
            } else if (dias <= 7) {
                razon = `Vence en esta semana (${dias} días restantes) (${t.fechaEntrega}).`;
            } else {
                razon = `Vence el ${t.fechaEntrega}. Prioridad base ajustada.`;
            }
        } else {
            const dif = parseInt(t.dificultad, 10);
            const con = parseInt(t.concentracion, 10);
            if (dif >= 4 && con >= 4) {
                razon = "Alta dificultad y concentración requerida sin fecha límite.";
            } else if (dif >= 4) {
                razon = "Tarea compleja que requiere esfuerzo sin fecha límite.";
            } else if (con >= 4) {
                razon = "Requiere alta concentración: mejor abordarla con energía.";
            }
        }
        
        return { ...t, puntaje, razon };
    });
    
    conPuntaje.sort((a, b) => b.puntaje - a.puntaje);

    const elegida = conPuntaje[0];

    let trabajo, descanso, mensaje;
    const basePuntaje = parseInt(elegida.dificultad, 10) + parseInt(elegida.concentracion, 10);
    if (basePuntaje >= 8) {
        trabajo = 40; descanso = 10;
        mensaje = `Carga exigente: bloque largo de 40 min para '${elegida.nombre}'.`;
    } else if (basePuntaje >= 6) {
        trabajo = 25; descanso = 5;
        mensaje = `Carga media: Pomodoro estándar de 25 min para '${elegida.nombre}'.`;
    } else {
        trabajo = 20; descanso = 5;
        mensaje = `Carga ligera: bloque ágil de 20 min para '${elegida.nombre}'.`;
    }

    const tareasOrdenadas = conPuntaje.map((t, i) => ({
        tarea_id:     t.id,
        tarea_nombre: t.nombre,
        prioridad:    i + 1,
        razon:        t.razon
    }));

    // --- Generación de Recomendaciones Dinámicas en JS ---
    const actividades = [];
    const nombreLower = elegida.nombre.toLowerCase();
    const esMental = /estudi|leer|exam|revis|tarea|matem|calcul|fisic|prog|codig|soft|dev/.test(nombreLower);
    const esFisica = /limpi|orden|habita|cocin|ejercicio|lavar/.test(nombreLower);
    const esComputadora = /prog|codig|soft|dev|comput|excel|word|pc|correo|email|chat/.test(nombreLower);

    if (esComputadora) {
        actividades.push("Mirar por la ventana a un punto lejano");
    } else if (esMental) {
        actividades.push("Hacer 5 rotaciones de cabeza muy lentas");
    } else if (esFisica) {
        actividades.push("Sentarse a relajar la espalda baja");
    } else {
        actividades.push("Estirar hombros y relajar el cuello");
    }

    if (descanso >= 10) {
        if (esMental) {
            actividades.push(`Caminar fuera del escritorio por ${descanso} min`);
        } else if (esFisica) {
            actividades.push(`Cerrar los ojos en un sofá por ${descanso} min`);
        } else {
            actividades.push(`Hacer estiramiento lumbar suave por ${descanso} min`);
        }
    } else {
        if (esMental) {
            actividades.push("Parpadear conscientemente diez veces");
        } else if (esFisica) {
            actividades.push("Sentarse y respirar hondo 5 veces");
        } else {
            actividades.push("Hacer círculos suaves con los tobillos");
        }
    }

    if (basePuntaje >= 8) {
        if (esMental) {
            actividades.push("Escuchar una melodía corta y suave");
        } else {
            actividades.push("Hacer estiramiento completo de pie");
        }
    } else {
        if (esComputadora) {
            actividades.push("Estirar cada uno de tus dedos");
        } else {
            actividades.push("Hacer círculos suaves con los hombros");
        }
    }

    return {
        tareas_priorizadas:   tareasOrdenadas,
        tarea_id:             elegida.id,
        tarea_nombre:         elegida.nombre,
        minutos_trabajo:      trabajo,
        minutos_descanso:     descanso,
        actividades_descanso: actividades,
        tipo_descanso:        "relajacion",
        mensaje
    };
}

/** Renderiza la lista ordenada de prioridades en la pantalla propuesta. */
function renderTareasPriorizadas(tareasPriorizadas) {
    const contenedor = $("propuesta-lista-prioridades");
    if (!contenedor) return;
    contenedor.innerHTML = "";
    if (!tareasPriorizadas || tareasPriorizadas.length === 0) return;

    tareasPriorizadas.forEach((tp) => {
        const div = document.createElement("div");
        div.className = "prioridad-item";
        div.innerHTML = `
            <span class="prioridad-num">#${tp.prioridad}</span>
            <div class="prioridad-info">
                <div class="prioridad-nombre">${escaparHtml(tp.tarea_nombre)}</div>
                <div class="prioridad-razon">${escaparHtml(tp.razon)}</div>
            </div>`;
        contenedor.appendChild(div);
    });
}

/** Renderiza las actividades de descanso sugeridas. */
function renderActividadesDescanso(actividades) {
    const contenedor = $("ejecucion-actividades-descanso");
    if (!contenedor) return;
    contenedor.innerHTML = "";
    if (!actividades || actividades.length === 0) return;

    actividades.forEach((act) => {
        const li = document.createElement("li");
        li.textContent = act; 
        contenedor.appendChild(li);
    });
}


// -----------------------------------------------------------------------------
// Generar propuesta — llama al agente IA
// -----------------------------------------------------------------------------

btnGenerarPropuesta.addEventListener("click", async () => {
    const pendientes = tareas.filter((t) => !t.terminada);
    if (pendientes.length === 0) {
        alert("Agrega o reactiva al menos una tarea pendiente para priorizar.");
        return;
    }

    // Estado de carga
    btnGenerarPropuesta.disabled = true;
    const textoOriginal = btnGenerarPropuesta.textContent;
    btnGenerarPropuesta.textContent = "Consultando IA...";

    let propuesta = null;
    let fuentePropuesta = "ia";

    try {
        const hoyStr = new Date().toISOString().split("T")[0];
        const resp = await fetch("/api/ia/propuesta", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ tareas: pendientes, fecha_actual: hoyStr })
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

        const data = await resp.json();
        if (data.ok && data.propuesta) {
            propuesta = data.propuesta;
            console.log("[IA] Propuesta recibida del backend:", propuesta);
        } else {
            throw new Error(data.error || "Respuesta inválida del servidor");
        }

    } catch (err) {
        console.warn("[IA] Error de red — usando fallback local:", err.message);
        propuesta = calcularPropuestaLocal(pendientes);
        fuentePropuesta = "local";
    } finally {
        btnGenerarPropuesta.disabled = false;
        btnGenerarPropuesta.textContent = textoOriginal;
    }

    if (!propuesta) return;

    // Resolver la tarea elegida desde la lista local
    const tareaElegida = tareas.find((t) => t.id === propuesta.tarea_id)
        || tareas.find((t) => t.nombre === propuesta.tarea_nombre)
        || tareas[0];

    // Actualizar estado global
    tareaSeleccionada = tareaElegida;
    minutosTrabajo    = propuesta.minutos_trabajo  || 25;
    minutosDescanso   = propuesta.minutos_descanso || 5;

    // Rellenar pantalla propuesta
    propuestaTarea.textContent         = propuesta.tarea_nombre || tareaElegida.nombre;
    propuestaDificultad.textContent    = tareaElegida ? tareaElegida.dificultad  : "—";
    propuestaConcentracion.textContent = tareaElegida ? tareaElegida.concentracion : "—";
    propuestaPuntaje.textContent       = tareaElegida
        ? parseInt(tareaElegida.dificultad, 10) + parseInt(tareaElegida.concentracion, 10)
        : "—";
    propuestaTrabajo.textContent  = minutosTrabajo;
    propuestaDescanso.textContent = minutosDescanso;
    propuestaMensaje.textContent  = propuesta.mensaje || "";

    // Mostrar fuente de la propuesta
    const fuenteEl = $("propuesta-fuente");
    if (fuenteEl) {
        fuenteEl.textContent = fuentePropuesta === "ia"
            ? "✨ Generado por el Agente Llama"
            : "⚡ Generado localmente (sin conexión a IA)";
        fuenteEl.className = "propuesta-fuente " + (fuentePropuesta === "ia" ? "fuente-ia" : "fuente-local");
        // Asegurar que sea visible (quitar oculto si estaba)
        fuenteEl.classList.remove("oculto");
    }

    // Renderizar prioridades
    renderTareasPriorizadas(propuesta.tareas_priorizadas);

    // Guardar actividades de descanso sugeridas globalmente
    actividadesDescansoSugeridas = propuesta.actividades_descanso || [];

    // Prellenar ajuste manual
    inputTrabajoManual.value  = minutosTrabajo;
    inputDescansoManual.value = minutosDescanso;

    bloqueAjuste.classList.add("oculto");
    btnIniciar.disabled = false;

    mostrarPantalla("propuesta");
});


// -----------------------------------------------------------------------------
// Botones propuesta
// -----------------------------------------------------------------------------

btnAceptarPropuesta.addEventListener("click", () => {
    iniciarPomodoro();
});

btnAjustarManual.addEventListener("click", () => {
    bloqueAjuste.classList.toggle("oculto");
});

btnVolverTareas.addEventListener("click", () => {
    mostrarPantalla("tareas");
});

btnIniciarManual.addEventListener("click", () => {
    const t = parseInt(inputTrabajoManual.value, 10);
    const d = parseInt(inputDescansoManual.value, 10);

    if (isNaN(t) || t < 1) return;
    if (isNaN(d) || d < 1) return;

    minutosTrabajo = t;
    minutosDescanso = d;

    iniciarPomodoro();
});


// -----------------------------------------------------------------------------
// Iniciar Pomodoro
// -----------------------------------------------------------------------------

async function iniciarPomodoro() {
    if (!tareaSeleccionada) {
        alert("Primero selecciona o genera una tarea.");
        return;
    }

    try {
        const resp = await fetch("/api/pomodoro/start", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                tarea: tareaSeleccionada.nombre,
                trabajo: minutosTrabajo,
                descanso: minutosDescanso,
                recomendaciones: actividadesDescansoSugeridas, // Enviamos las generadas por la IA
                duracion: minutosTrabajo,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            alert("Error al iniciar: " + (err.mensaje || err.error || resp.status));
            return;
        }

        mostrarPantalla("ejecucion");
        consultarEstado();

    } catch (e) {
        console.error("[POMODORO] Error al iniciar:", e);
        alert("No se pudo conectar con el servidor.");
    }
}


// -----------------------------------------------------------------------------
// Botones ejecución
// -----------------------------------------------------------------------------

btnIniciar.addEventListener("click", iniciarPomodoro);

btnPausar.addEventListener("click", async () => {
    await fetch("/api/pomodoro/pause", {
        method: "POST",
    }).catch(() => {});

    consultarEstado();
});

btnReanudar.addEventListener("click", async () => {
    await fetch("/api/pomodoro/resume", {
        method: "POST",
    }).catch(() => {});

    consultarEstado();
});

btnFinalizar.addEventListener("click", async () => {

    try {

        const resp = await fetch("/api/pomodoro/skip", {
            method: "POST",
        });

        const data = await resp.json();

        console.log("Skip:", data);

        consultarEstado();

        // Si terminó todo el ciclo
        if (data.nuevo_modo === "IDLE") {
            mostrarPantalla("final");
        }

    } catch (e) {

        console.error(e);

        alert("No se pudo saltar la fase.");
    }
});

btnVolverDesdeEjecucion.addEventListener("click", () => {
    mostrarPantalla("tareas");
});

btnFinalVolverTareas.addEventListener("click", () => {
    renderListaTareas();
    mostrarPantalla("tareas");
});

btnContinuarBloque.addEventListener("click", () => {
    if (!tareaSeleccionada) {
        mostrarPantalla("tareas");
        return;
    }

    iniciarPomodoro();
});

btnMarcarTerminada.addEventListener("click", () => {
    if (tareaSeleccionada) {
        const idx = tareas.findIndex((t) => t.id === tareaSeleccionada.id);

        if (idx !== -1) {
            tareas[idx].terminada = true; // Marcar como terminada dentro del arreglo
        }
    }

    tareaSeleccionada = null;
    renderListaTareas();
    mostrarPantalla("tareas");
});

// -----------------------------------------------------------------------------
// Consultar estado backend
// -----------------------------------------------------------------------------

async function consultarEstado() {
    try {
        const resp = await fetch("/api/pomodoro/status");

        if (!resp.ok) return;

        const datos = await resp.json();

        renderEjecucion(datos);

    } catch (e) {
        // Evita llenar la consola si el backend se cae momentáneamente.
    }
}


// -----------------------------------------------------------------------------
// Render ejecución
// -----------------------------------------------------------------------------

function renderEjecucion({
    modo,
    tarea_actual,
    tiempo_restante,
    recomendaciones
}) {
    execModo.textContent = modo;

    execModo.className =
        "badge " +
        ({
            "IDLE": "badge-idle",
            "TRABAJANDO": "badge-work",
            "DESCANSO": "badge-break",
            "PAUSADO": "badge-paused",
        }[modo] || "badge-idle");

    execTarea.textContent = tarea_actual || "—";
    execTiempo.textContent = formatearSegundos(tiempo_restante);

    // Mostrar actividades sugeridas solo si estamos en DESCANSO
    const bloqueDescanso = $("bloque-actividades-ejecucion");
    if (modo === "DESCANSO") {
        if (bloqueDescanso) bloqueDescanso.classList.remove("oculto");
        renderActividadesDescanso(recomendaciones || []);
    } else {
        if (bloqueDescanso) bloqueDescanso.classList.add("oculto");
    }

    btnIniciar.disabled =
        (
            modo === "TRABAJANDO" ||
            modo === "PAUSADO" ||
            modo === "DESCANSO"
        ) || !tareaSeleccionada;

    btnPausar.disabled = modo !== "TRABAJANDO";
    btnReanudar.disabled = modo !== "PAUSADO";
    btnFinalizar.disabled = modo === "IDLE";
    if (modo === "IDLE" && pantallaEjecucion && !pantallaEjecucion.classList.contains("oculto")) {
    mostrarPantalla("final");
}
}


// -----------------------------------------------------------------------------
// Inicialización
// -----------------------------------------------------------------------------

// Llenar dinámicamente los días de 1 a 31
if (selectDia) {
    for (let d = 1; d <= 31; d++) {
        const opt = document.createElement("option");
        const dStr = d.toString().padStart(2, "0");
        opt.value = dStr;
        opt.textContent = dStr;
        selectDia.appendChild(opt);
    }
}

renderListaTareas();
mostrarPantalla("tareas");
consultarEstado();

intervalStatus = setInterval(consultarEstado, 1000);