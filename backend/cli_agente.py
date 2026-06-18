# =============================================================================
# backend/cli_agente.py — Interfaz de Consola (CLI) Interactiva para el Agente Pomodoro
# =============================================================================

import os
import sys
import time
import json

# Asegurar que se puedan importar módulos de 'services' sin problemas
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importar lógica del Agente Inteligente Pomodoro
try:
    from services.agente import generar_propuesta_pomodoro
except ImportError:
    print("❌ Error: No se pudo importar el módulo 'services.agente'.")
    print("Asegúrate de estar ejecutando el script desde la carpeta del backend o que esté en la ruta correcta.")
    sys.exit(1)

# Cargar variables de entorno del archivo .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuración de Colores con Colorama (con fallback seguro)
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    HAS_COLORS = True
except ImportError:
    HAS_COLORS = False
    # Mocking para evitar fallos si no está instalado
    class MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = MockColor()

# Configuración de pitidos según plataforma
def hacer_pitido(tipo="trabajo"):
    try:
        if sys.platform == "win32":
            import winsound
            if tipo == "trabajo":
                winsound.Beep(880, 500)
                time.sleep(0.1)
                winsound.Beep(880, 500)
            else:
                winsound.Beep(440, 1000)
        else:
            # Fallback Unix/OS X
            print("\a", end="", flush=True)
    except Exception:
        pass

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    print(Fore.CYAN + "=====================================================================")
    print(Fore.CYAN + "   🧠  BIENVENIDO AL AGENTE POMODORO IA EN CONSOLA (MODO CLI)  🧠   ")
    print(Fore.CYAN + "=====================================================================")
    
    # Informar estado de la API de Groq
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if api_key:
        print(Fore.GREEN + "  🟢 [ESTADO IA] Groq API Key configurada. Conexión Llama 3 activa.")
    else:
        print(Fore.YELLOW + "  🟡 [ESTADO IA] Sin API Key. Usando el Motor de Priorización Local (Fallback).")
    print(Fore.CYAN + "=====================================================================\n")

def menu_principal():
    limpiar_pantalla()
    mostrar_banner()
    print("Elige una opción:")
    print(Fore.YELLOW + "  [1]" + " Ingresar tareas manualmente")
    print(Fore.YELLOW + "  [2]" + " Usar tareas de demostración predefinidas (rápido)")
    print(Fore.YELLOW + "  [3]" + " Salir")
    print()
    opcion = input("Selecciona una opción [1-3]: ").strip()
    return opcion

def pedir_tareas_manualmente():
    tareas = []
    limpiar_pantalla()
    mostrar_banner()
    print(Fore.CYAN + "✏️  INGRESO MANUAL DE TAREAS")
    print("---------------------------------------------------------------------")
    
    while True:
        try:
            num_tareas = input("¿Cuántas tareas deseas priorizar? (mínimo 1): ").strip()
            num_tareas = int(num_tareas)
            if num_tareas < 1:
                print(Fore.RED + "Por favor, ingresa un número mayor o igual a 1.")
                continue
            break
        except ValueError:
            print(Fore.RED + "Por favor, ingresa un número válido.")

    for i in range(1, num_tareas + 1):
        print(Fore.GREEN + f"\nTarea #{i}:")
        nombre = input("  🔹 Nombre de la tarea: ").strip()
        while not nombre:
            nombre = input(Fore.RED + "  ⚠️ El nombre no puede estar vacío. Escribe el nombre: ").strip()
        
        # Pedir Dificultad
        dificultad = 3
        while True:
            try:
                dif_input = input("  🔹 Dificultad (1 = muy fácil, 5 = muy difícil) [1-5]: ").strip()
                dificultad = int(dif_input)
                if 1 <= dificultad <= 5:
                    break
                print(Fore.RED + "  ⚠️ Debe ser un número del 1 al 5.")
            except ValueError:
                print(Fore.RED + "  ⚠️ Entrada inválida. Ingresa un número entero del 1 al 5.")
        
        # Pedir Concentración
        concentracion = 3
        while True:
            try:
                con_input = input("  🔹 Concentración requerida (1 = baja, 5 = máxima) [1-5]: ").strip()
                concentracion = int(con_input)
                if 1 <= concentracion <= 5:
                    break
                print(Fore.RED + "  ⚠️ Debe ser un número del 1 al 5.")
            except ValueError:
                print(Fore.RED + "  ⚠️ Entrada inválida. Ingresa un número entero del 1 al 5.")

        tareas.append({
            "id": f"t{i}",
            "nombre": nombre,
            "dificultad": dificultad,
            "concentracion": concentracion
        })
        
    return tareas

def obtener_tareas_demostracion():
    print(Fore.GREEN + "\nCargando tareas de demostración predefinidas...")
    time.sleep(0.5)
    return [
        {"id": "t1", "nombre": "Desarrollar el CLI del Agente Pomodoro para el Profesor", "dificultad": 5, "concentracion": 5},
        {"id": "t2", "nombre": "Revisar correos del equipo y coordinar entregas", "dificultad": 2, "concentracion": 2},
        {"id": "t3", "nombre": "Escribir la documentación del proyecto final", "dificultad": 4, "concentracion": 4},
        {"id": "t4", "nombre": "Limpiar y ordenar los cables del prototipo ESP32", "dificultad": 3, "concentracion": 2}
    ]

def dibujar_tabla_prioridades(tareas_priorizadas):
    print(Fore.CYAN + "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════╗")
    print(Fore.CYAN + "║                                  TAREAS PRIORIZADAS POR EL AGENTE IA                                      ║")
    print(Fore.CYAN + "╠═══════╦═════════════════════════════════════════════╦═════════════════════════════════════════════════════╣")
    print(Fore.CYAN + "║ Prior ║ Tarea                                       ║ Razón de la Priorización                            ║")
    print(Fore.CYAN + "╠═══════╬═════════════════════════════════════════════╬═════════════════════════════════════════════════════╣")
    
    for t in tareas_priorizadas:
        prior = str(t.get("prioridad", "?"))
        nombre = t.get("tarea_nombre", "")
        # Truncar nombre si es muy largo para la tabla
        if len(nombre) > 42:
            nombre = nombre[:39] + "..."
        razon = t.get("razon", "")
        if len(razon) > 50:
            razon = razon[:47] + "..."
            
        print(f"║ {prior.center(5)} ║ {nombre.ljust(43)} ║ {razon.ljust(51)} ║")
        
    print(Fore.CYAN + "╚═══════╩═════════════════════════════════════════════╩═════════════════════════════════════════════════════╝")

def ejecutar_cuenta_regresiva(nombre_fase, total_minutos, modo_demo, color_fase):
    # En modo demostración rápida, 1 segundo equivale a 1 minuto
    segundos_totales = total_minutos if modo_demo else total_minutos * 60
    
    # Si es modo demo, avisar del factor rápido
    unidad = "minutos (simulados en segundos)" if modo_demo else "minutos"
    print(color_fase + f"\n=== Fase: {nombre_fase.upper()} ({total_minutos} {unidad}) ===")
    
    ancho_barra = 40
    inicio = time.time()
    
    try:
        while True:
            transcurrido = time.time() - inicio
            if transcurrido >= segundos_totales:
                break
                
            restante = max(0, segundos_totales - int(transcurrido))
            
            # Calcular minutos y segundos para mostrar en pantalla
            if modo_demo:
                # En modo demo mostramos los segundos reales simulando minutos
                min_pantalla = restante
                seg_pantalla = 0
            else:
                min_pantalla = restante // 60
                seg_pantalla = restante % 60
                
            # Calcular porcentaje y barra de progreso
            porcentaje = (transcurrido / segundos_totales)
            bloques = int(porcentaje * ancho_barra)
            barra = "█" * bloques + "░" * (ancho_barra - bloques)
            
            # Actualizar en la misma línea con retorno de carro
            sys.stdout.write(
                color_fase + 
                f"\r  [{barra}] {int(porcentaje * 100)}% | ⏰ Restante: {min_pantalla:02d}:{seg_pantalla:02d} | Presiona Ctrl+C para interrumpir"
            )
            sys.stdout.flush()
            time.sleep(0.1)
            
        # Al terminar, pintar la barra al 100%
        barra_completa = "█" * ancho_barra
        sys.stdout.write(color_fase + f"\r  [{barra_completa}] 100% | ⏰ Restante: 00:00 | ¡Fase Completada!             \n")
        sys.stdout.flush()
        
    except KeyboardInterrupt:
        print(Fore.RED + "\n\n⚠️ Temporizador interrumpido por el usuario.")
        return False
        
    return True

def iniciar_temporizador_pomodoro(propuesta):
    tarea_nombre = propuesta.get("tarea_nombre", "Tarea seleccionada")
    min_trabajo = propuesta.get("minutos_trabajo", 25)
    min_descanso = propuesta.get("minutos_descanso", 5)
    actividades = propuesta.get("actividades_descanso", [])
    
    print("\n---------------------------------------------------------------------")
    opcion = input("¿Deseas iniciar el temporizador Pomodoro para esta tarea? (s/n): ").strip().lower()
    
    if opcion != 's':
        print(Fore.YELLOW + "\nTemporizador omitido. Volviendo al menú principal...")
        time.sleep(1.5)
        return
        
    # Preguntar el modo de ejecución
    limpiar_pantalla()
    mostrar_banner()
    print(Fore.CYAN + "⏱️  CONFIGURACIÓN DEL TEMPORIZADOR")
    print("---------------------------------------------------------------------")
    print("Elige el modo de velocidad:")
    print("  [1] Tiempo Real (1 minuto real = 1 minuto de reloj)")
    print("  [2] Demostración Rápida (1 segundo real = 1 minuto simulado) " + Fore.GREEN + "[RECOMENDADO para el Profesor]")
    print()
    
    modo_sel = input("Selecciona [1-2]: ").strip()
    modo_demo = True if modo_sel == "2" else False
    
    limpiar_pantalla()
    mostrar_banner()
    print(Fore.GREEN + f"🎯 Iniciando Pomodoro: '{tarea_nombre}'")
    print(Fore.WHITE + f"   - Trabajo: {min_trabajo} minutos")
    print(Fore.WHITE + f"   - Descanso: {min_descanso} minutos")
    print("---------------------------------------------------------------------")
    
    # 1. Fase de Trabajo
    print(Fore.RED + "\n⚡ ¡HORA DE TRABAJAR! Concéntrate plenamente en tu tarea.")
    hacer_pitido("trabajo")
    
    completado = ejecutar_cuenta_regresiva(
        nombre_fase="Trabajo", 
        total_minutos=min_trabajo, 
        modo_demo=modo_demo, 
        color_fase=Fore.RED
    )
    
    if not completado:
        input("\nPresiona Enter para regresar al menú...")
        return
        
    # 2. Fase de Descanso
    hacer_pitido("descanso")
    print(Fore.GREEN + "\n☕ ¡TIEMPO DE DESCANSO! Suelta el teclado, levántate y relájate.")
    print(Fore.GREEN + "Recomendaciones de salud del Agente:")
    for idx, act in enumerate(actividades, 1):
        print(Fore.GREEN + f"  [{idx}] {act}")
        
    completado = ejecutar_cuenta_regresiva(
        nombre_fase="Descanso", 
        total_minutos=min_descanso, 
        modo_demo=modo_demo, 
        color_fase=Fore.GREEN
    )
    
    if completado:
        hacer_pitido("trabajo")
        print(Fore.CYAN + "\n🎉 ¡Excelente! Has completado con éxito este bloque de Pomodoro.")
        print(Fore.CYAN + "Tu cuerpo y tu mente te lo agradecerán. ¡Sigue así!")
        
    input("\nPresiona Enter para regresar al menú principal...")

def main():
    while True:
        opcion = menu_principal()
        
        if opcion == "3":
            print(Fore.CYAN + "\n👋 ¡Gracias por usar el Asistente Pomodoro IA! ¡Hasta luego!\n")
            break
            
        elif opcion in ("1", "2"):
            if opcion == "1":
                tareas = pedir_tareas_manualmente()
            else:
                tareas = obtener_tareas_demostracion()
                # Mostrar tareas cargadas
                print("\nTareas Cargadas:")
                for t in tareas:
                    print(f"  - {t['nombre']} (Dif: {t['dificultad']}, Conc: {t['concentracion']})")
            
            if not tareas:
                print(Fore.RED + "\nNo se agregaron tareas válidas.")
                time.sleep(2)
                continue
                
            # Animación de procesamiento
            print(Fore.CYAN + "\n🧠 Enviando datos al Agente Pomodoro...", end="", flush=True)
            for _ in range(3):
                time.sleep(0.4)
                print(".", end="", flush=True)
            print()
            
            try:
                # Llamada unificada al agente
                propuesta = generar_propuesta_pomodoro(tareas)
                
                limpiar_pantalla()
                mostrar_banner()
                
                # Dibujar tabla
                dibujar_tabla_prioridades(propuesta.get("tareas_priorizadas", []))
                
                # Mostrar propuesta ganadora
                print(Fore.YELLOW + "\n👑 PROPUESTA RECOMENDADA POR EL AGENTE IA:")
                print(Fore.WHITE + f"   📌 Tarea Elegida: " + Fore.GREEN + f"'{propuesta.get('tarea_nombre')}'")
                print(Fore.WHITE + f"   ⏱️ Duración Trabajo : " + Fore.RED + f"{propuesta.get('minutos_trabajo')} minutos")
                print(Fore.WHITE + f"   ☕ Duración Descanso: " + Fore.GREEN + f"{propuesta.get('minutos_descanso')} minutos")
                print(Fore.WHITE + f"   🎨 Tipo de Descanso : " + Fore.CYAN + f"{propuesta.get('tipo_descanso').upper()}")
                print(Fore.WHITE + f"   💬 Explicación      : " + Fore.WHITE + f"\"{propuesta.get('mensaje')}\"")
                
                print(Fore.GREEN + "\n🌱 Recomendaciones de salud personalizadas para el descanso:")
                for idx, act in enumerate(propuesta.get("actividades_descanso", []), 1):
                    print(Fore.GREEN + f"   [{idx}] {act}")
                
                # Iniciar el temporizador si lo desean
                iniciar_temporizador_pomodoro(propuesta)
                
            except Exception as e:
                print(Fore.RED + f"\n❌ Error al procesar la propuesta con el agente: {e}")
                input("\nPresiona Enter para continuar...")
        else:
            print(Fore.RED + "\nOpción inválida. Elige 1, 2 o 3.")
            time.sleep(1.5)

if __name__ == "__main__":
    main()
