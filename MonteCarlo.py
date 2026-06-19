import csv
import random
import numpy as np

def cargar_datos():
    equipos = {}
    with open('player_mundial.csv', mode='r', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        for fila in lector:
            seleccion = fila['seleccion']
            if seleccion not in equipos:
                equipos[seleccion] = []
            equipos[seleccion].append(fila)

    grupos = {}
    with open('fase_grupos.csv', mode='r', encoding='utf-8-sig') as f:
        lector = csv.DictReader(f)
        for fila in lector:
            grupos[fila['Grupo']] = [fila['Equipo1'], fila['Equipo2'], fila['Equipo3'], fila['Equipo4']]

    return equipos, grupos


def sortear_lesiones(bd_jugadores):
    """
    Sortea UNA SOLA VEZ al inicio de cada iteración qué jugadores están lesionados durante todo el Mundial. Devuelve un dict {seleccion: set(indices_lesionados)}.
    """
    lesionados = {}
    for seleccion, jugadores in bd_jugadores.items():
        lesionados[seleccion] = set()
        for idx, j in enumerate(jugadores):
            prob = float(j.get('Prob_Lesion_Mundial_%', 0)) / 100.0
            if random.random() < prob:
                lesionados[seleccion].add(idx)
    return lesionados


def calcular_poder_equipo(jugadores, indices_lesionados):
    """
    Construye el XI ideal respetando la formación 1-4-3-3, usando los jugadores sanos ordenados por Puntuación dentro de cada puesto.
    """
    sanos_por_pos = {'Portero': [], 'Defensa': [], 'Mediocampista': [], 'Delantero': []}

    for idx, j in enumerate(jugadores):
        if idx in indices_lesionados:
            continue
        pos = j.get('posicion', 'Mediocampista')
        puntuacion = float(j.get('Puntuacion', 0))
        sanos_por_pos.setdefault(pos, []).append(puntuacion)

    for pos in sanos_por_pos:
        sanos_por_pos[pos].sort(reverse=True)

    cuotas = {'Portero': 1, 'Defensa': 4, 'Mediocampista': 3, 'Delantero': 3}
    titulares = []
    reservas_globales = []

    for pos, cuota in cuotas.items():
        disponibles = sanos_por_pos[pos]
        titulares.extend(disponibles[:cuota])
        reservas_globales.extend(disponibles[cuota:])

    if len(titulares) < 11:
        reservas_globales.sort(reverse=True)
        huecos = 11 - len(titulares)
        titulares.extend(reservas_globales[:huecos])

    return max(sum(titulares), 1)



EXP_PODER = 1.3   # exponente de la fórmula pitagórica


def simular_partido(equipoA, equipoB, poderes, es_grupo=False):

    pA = poderes[equipoA] ** EXP_PODER
    pB = poderes[equipoB] ** EXP_PODER

    base = 1.5  # media de goles por equipo aprox

    lambda_A = base * (pA / (pA + pB))
    lambda_B = base * (pB / (pA + pB))

    goles_A = np.random.poisson(lambda_A)
    goles_B = np.random.poisson(lambda_B)

    if goles_A > goles_B:
        return equipoA
    elif goles_B > goles_A:
        return equipoB

    if es_grupo:
        return "Empate"

    return random.choice([equipoA, equipoB]) # En caso de empate en fase de eliminación seria por penaltis (aleatorio)


def simular_fase_grupos(grupos, poderes):
    """
    Clasificación dentro del grupo:
      1. Puntos
      2. Puntos H2H (mini-liga entre empatados)
      3. Sorteo aleatorio

    Clasificación de terceros entre grupos:
      1. Puntos
      2. Sorteo aleatorio
    """
    primeros       = []
    segundos       = []
    todos_terceros = []

    for nombre_grupo in sorted(grupos.keys()):
        equipos = grupos[nombre_grupo]
        puntos = {eq: 0 for eq in equipos}
        h2h = {eq: {opp: 0 for opp in equipos if opp != eq} for eq in equipos}

        for i in range(4):
            for j in range(i + 1, 4):
                eqA, eqB = equipos[i], equipos[j]
                resultado = simular_partido(eqA, eqB, poderes, es_grupo=True)

                if resultado == "Empate":
                    puntos[eqA] += 1
                    puntos[eqB] += 1
                    h2h[eqA][eqB] += 1
                    h2h[eqB][eqA] += 1
                elif resultado == eqA:
                    puntos[eqA] += 3
                    h2h[eqA][eqB] += 3
                else:
                    puntos[eqB] += 3
                    h2h[eqB][eqA] += 3

        clasificacion = _resolver_clasificacion(equipos, puntos, h2h)

        primeros.append(clasificacion[0])
        segundos.append(clasificacion[1])
        todos_terceros.append((clasificacion[2], nombre_grupo, puntos[clasificacion[2]]))

    # ── Selección de los 8 mejores terceros ──────────────────────────────
    todos_terceros.sort(key=lambda x: (x[2], random.random()), reverse=True)
    mejores_terceros             = [t[0] for t in todos_terceros[:8]]
    grupos_terceros_clasificados = [t[1] for t in todos_terceros[:8]]

    return primeros, segundos, mejores_terceros, grupos_terceros_clasificados


def _resolver_clasificacion(equipos, puntos, h2h):
    """
    Ordena los 4 equipos del grupo por:
      1. Puntos globales
      2. Puntos H2H (mini-liga entre empatados)
      3. Sorteo aleatorio

    h2h[eqA][eqB] = puntos que eqA obtuvo contra eqB (0, 1 o 3).
    """
    pre_orden = sorted(equipos, key=lambda eq: puntos[eq], reverse=True)

    resultado = []
    i = 0
    while i < len(pre_orden):
        j = i + 1
        while j < len(pre_orden) and puntos[pre_orden[j]] == puntos[pre_orden[i]]:
            j += 1
        bloque = pre_orden[i:j]

        if len(bloque) == 1:
            resultado.extend(bloque)
        else:
            resultado.extend(_desempate_h2h(bloque, h2h))
        i = j
    return resultado


def _desempate_h2h(bloque, h2h):
    """
    Mini-liga H2H iterativa entre equipos empatados en puntos.

    Calcula los puntos H2H de cada equipo sumando únicamente los
    resultados contra los rivales del bloque. Si siguen empatados,
    itera un nivel más. Si persiste: sorteo aleatorio.
    """
    def pts_h2h(eq, rivals):
        return sum(h2h[eq][opp] for opp in rivals if opp != eq)

    def ordenar_bloque(sub, profundidad=0):
        if len(sub) <= 1:
            return sub

        claves = {eq: pts_h2h(eq, sub) for eq in sub}
        ordenado = sorted(sub, key=lambda e: claves[e], reverse=True)

        if profundidad >= 2:
            return sorted(ordenado, key=lambda _: random.random())

        resultado_local = []
        i = 0
        while i < len(ordenado):
            j = i + 1
            while j < len(ordenado) and claves[ordenado[j]] == claves[ordenado[i]]:
                j += 1
            sub_sub = ordenado[i:j]
            if len(sub_sub) == 1:
                resultado_local.extend(sub_sub)
            else:
                resultado_local.extend(ordenar_bloque(sub_sub, profundidad + 1))
            i = j
        return resultado_local

    return ordenar_bloque(list(bloque))


# Orden fijo de los partidos con terceros en el R32
_SLOTS_TERCEROS = ['M74', 'M77', 'M79', 'M80', 'M81', 'M82', 'M85', 'M87']


# Preferencias oficiales de grupo por slot (del Anexo IV FIFA 2026)
_SLOT_PREFERENCIAS = {
    'M74': list('ABCDF'),
    'M77': list('CDFGH'),
    'M79': list('CEFHI'),
    'M80': list('EHIJK'),
    'M81': list('BEFIJ'),
    'M82': list('AEHIJ'),
    'M85': list('EFGIJ'),
    'M87': list('DEIJL'),
}


def _asignar_terceros_oficial(grupos_clasificados):
    """
    Asigna los 8 terceros clasificados a sus slots del bracket R32
    siguiendo las preferencias oficiales del Anexo IV FIFA 2026.

    Usa un algoritmo greedy con backtracking para garantizar una
    asignación válida (biyección grupos → slots).

    Parámetros:
        grupos_clasificados : lista de 8 strings (letras de grupo A-L)

    Retorna:
        dict { slot → letra_de_grupo } con los 8 slots asignados.
    """
    disponibles = list(grupos_clasificados)  

    def backtrack(slot_idx, asignados, restantes):
        if slot_idx == len(_SLOTS_TERCEROS):
            return asignados if not restantes else None
        slot = _SLOTS_TERCEROS[slot_idx]
        prefs = _SLOT_PREFERENCIAS[slot]
        candidatos = [g for g in prefs if g in restantes] + \
                     [g for g in restantes if g not in prefs]
        for grupo in candidatos:
            nuevos_restantes = [g for g in restantes if g != grupo]
            resultado = backtrack(slot_idx + 1,
                                  {**asignados, slot: grupo},
                                  nuevos_restantes)
            if resultado is not None:
                return resultado
        return None  # no solution (shouldn't happen with 8 groups / 8 slots)

    asignacion = backtrack(0, {}, disponibles)
    if asignacion is None:
        asignacion = {slot: grupos_clasificados[i]
                      for i, slot in enumerate(_SLOTS_TERCEROS)}
    return asignacion


def construir_bracket_r32(primeros, segundos, mejores_terceros, grupos_terceros_clasificados):
    """
    Construye los 16 partidos del R32 usando la asignación oficial de terceros del Anexo IV del Reglamento FIFA Copa del Mundo 2026.
    """
    p = primeros    # p[0]=1A … p[11]=1L
    s = segundos    # s[0]=2A … s[11]=2L
    g = {letra: idx for idx, letra in enumerate('ABCDEFGHIJKL')}

    # ── Asignación oficial de terceros a slots ──────────────────────────
    asignacion = _asignar_terceros_oficial(list(grupos_terceros_clasificados))

    # Construir mapa grupo → equipo_tercero
    grupo_a_tercero = {grupos_terceros_clasificados[i]: mejores_terceros[i]
                       for i in range(len(mejores_terceros))}

    def tercero(slot):
        grupo = asignacion[slot]
        return grupo_a_tercero[grupo]

    return [
        (s[g['A']], s[g['B']]),            # M73: 2A vs 2B
        (p[g['E']], tercero('M74')),        # M74: 1E vs 3(oficial)
        (p[g['F']], s[g['C']]),            # M75: 1F vs 2C
        (p[g['C']], s[g['F']]),            # M76: 1C vs 2F
        (p[g['I']], tercero('M77')),        # M77: 1I vs 3(oficial)
        (s[g['E']], s[g['I']]),            # M78: 2E vs 2I
        (p[g['A']], tercero('M79')),        # M79: 1A vs 3(oficial)
        (p[g['L']], tercero('M80')),        # M80: 1L vs 3(oficial)
        (p[g['D']], tercero('M81')),        # M81: 1D vs 3(oficial)
        (p[g['G']], tercero('M82')),        # M82: 1G vs 3(oficial)
        (s[g['K']], s[g['L']]),            # M83: 2K vs 2L
        (p[g['H']], s[g['J']]),            # M84: 1H vs 2J
        (p[g['B']], tercero('M85')),        # M85: 1B vs 3(oficial)
        (p[g['J']], s[g['H']]),            # M86: 1J vs 2H
        (p[g['K']], tercero('M87')),        # M87: 1K vs 3(oficial)
        (s[g['D']], s[g['G']]),            # M88: 2D vs 2G
    ]



def jugar_ronda_fija(partidos, poderes):
    ganadores = []
    for equipoA, equipoB in partidos:
        ganador = simular_partido(equipoA, equipoB, poderes, es_grupo=False)
        ganadores.append(ganador)
    return ganadores


def construir_r16(W):
    return [
        (W[1],  W[4]),   # M89: W74 vs W77
        (W[0],  W[2]),   # M90: W73 vs W75
        (W[3],  W[5]),   # M91: W76 vs W78
        (W[6],  W[7]),   # M92: W79 vs W80
        (W[10], W[11]),  # M93: W83 vs W84
        (W[8],  W[9]),   # M94: W81 vs W82
        (W[13], W[15]),  # M95: W86 vs W88
        (W[12], W[14]),  # M96: W85 vs W87
    ]


def construir_qf(W):
    return [
        (W[0], W[1]),   # QF1 (M97): W89 vs W90
        (W[4], W[5]),   # QF2 (M98): W93 vs W94
        (W[2], W[3]),   # QF3 (M99): W91 vs W92
        (W[6], W[7]),   # QF4(M100): W95 vs W96
    ]


def construir_sf(W):
    return [
        (W[0], W[1]),   # SF1(M101): W97 vs W98
        (W[2], W[3]),   # SF2(M102): W99 vs W100
    ]


def ejecutar_montecarlo(simulaciones=1000):
    print("Cargando bases de datos...")
    bd_jugadores, bd_grupos = cargar_datos()
    todos_los_equipos = list(bd_jugadores.keys())

    resultados = {
        eq: {'Grupos': 0, 'Dieciseisavos': 0, 'Octavos': 0,
             'Cuartos': 0, 'Semis': 0, 'Finalista': 0, 'Campeon': 0}
        for eq in todos_los_equipos
    }

    print(f"Iniciando {simulaciones:,} simulaciones de Monte Carlo...")

    for i in range(simulaciones):

        # A) SORTEO DE LESIONES
        lesionados = sortear_lesiones(bd_jugadores)

        # B) CALCULAR PODERES
        poderes_torneo = {
            eq: calcular_poder_equipo(bd_jugadores[eq], lesionados[eq])
            for eq in todos_los_equipos
        }

        # C) FASE DE GRUPOS
        primeros, segundos, mejores_3os, grupos_3os = simular_fase_grupos(
            bd_grupos, poderes_torneo
        )

        clasificados_r32 = set(primeros) | set(segundos) | set(mejores_3os)
        for eq in todos_los_equipos:
            if eq not in clasificados_r32:
                resultados[eq]['Grupos'] += 1

        # D) R32: DIECISEISAVOS (32 → 16)
        bracket_r32  = construir_bracket_r32(primeros, segundos, mejores_3os, grupos_3os)
        ganadores_r32 = jugar_ronda_fija(bracket_r32, poderes_torneo)

        for eq in clasificados_r32 - set(ganadores_r32):
            resultados[eq]['Dieciseisavos'] += 1

        # E) R16: OCTAVOS (16 → 8)
        ganadores_r16 = jugar_ronda_fija(construir_r16(ganadores_r32), poderes_torneo)
        for eq in set(ganadores_r32) - set(ganadores_r16):
            resultados[eq]['Octavos'] += 1

        # F) CUARTOS (8 → 4)
        ganadores_qf = jugar_ronda_fija(construir_qf(ganadores_r16), poderes_torneo)
        for eq in set(ganadores_r16) - set(ganadores_qf):
            resultados[eq]['Cuartos'] += 1

        # G) SEMIFINALES (4 → 2)
        ganadores_sf = jugar_ronda_fija(construir_sf(ganadores_qf), poderes_torneo)
        for eq in set(ganadores_qf) - set(ganadores_sf):
            resultados[eq]['Semis'] += 1

        # H) FINAL (2 → 1)
        finalistas = list(ganadores_sf)
        campeon    = jugar_ronda_fija([(finalistas[0], finalistas[1])], poderes_torneo)[0]
        finalista  = finalistas[1] if campeon == finalistas[0] else finalistas[0]

        resultados[finalista]['Finalista'] += 1
        resultados[campeon]['Campeon']     += 1

        if (i + 1) % 1000 == 0:
            print(f"  ... {i + 1:,} simulaciones completadas")

    return resultados


# ==========================================
# 4. EXPORTAR RESULTADOS
# ==========================================

if __name__ == '__main__':
    NUM_SIMULACIONES = 50000
    resultados_finales = ejecutar_montecarlo(NUM_SIMULACIONES)

    with open('resultados_montecarlo.csv', mode='w', encoding='utf-8-sig', newline='') as f:
        escritor = csv.writer(f)
        escritor.writerow(['Seleccion', 'Grupos_%', 'Dieciseisavos_%', 'Octavos_%', 'Cuartos_%', 'Semis_%', 'Finalista_%', 'Campeon_%'])
        
        for equipo, res in resultados_finales.items():
            g_pct = (res['Grupos'] / NUM_SIMULACIONES) * 100
            d_pct = (res['Dieciseisavos'] / NUM_SIMULACIONES) * 100
            o_pct = (res['Octavos'] / NUM_SIMULACIONES) * 100
            c_pct = (res['Cuartos'] / NUM_SIMULACIONES) * 100
            s_pct = (res['Semis'] / NUM_SIMULACIONES) * 100
            f_pct = (res['Finalista'] / NUM_SIMULACIONES) * 100
            w_pct = (res['Campeon'] / NUM_SIMULACIONES) * 100
            
            escritor.writerow([equipo, round(g_pct,2), round(d_pct,2), round(o_pct,2), round(c_pct,2), round(s_pct,2), round(f_pct,2), round(w_pct,2)])
            
    print("¡Simulación terminada! Revisa el archivo 'resultados_montecarlo.csv'")
