# FIFA-2026-Outcome-Predictor

A probabilistic tournament simulation based on player market values, injury modelling and Poisson goal generation.

---

## Índice

1. [Idea general del modelo](#1-idea-general-del-modelo)
2. [Datos de entrada](#2-datos-de-entrada)
   - 2.1 [Cálculo de los valores del modelo](#21-cálculo-de-los-valores-del-modelo)
3. [Cálculo de fuerza de cada selección](#3-cálculo-de-fuerza-de-cada-selección)
   - 3.1 [Lesiones](#31-lesiones)
   - 3.2 [Once ideal](#32-once-ideal)
   - 3.3 [Poder del equipo](#33-poder-del-equipo)
4. [Simulación de partidos](#4-simulación-de-partidos)
   - 4.1 [Modelo de Poisson (goles)](#42-modelo-de-poisson-goles)
5. [Fase de grupos](#5-fase-de-grupos)
6. [Fase eliminatoria](#6-fase-eliminatoria)
7. [Simulación Monte Carlo](#7-simulación-monte-carlo)
8. [Resultados finales](#8-resultados-finales)
9. [Conclusión](#9-conclusión)

---

## 1. Idea general del modelo

El simulador transforma datos de jugadores individuales en una fuerza global por selección y, a partir de ella, simula miles de Mundiales completos mediante un enfoque de Monte Carlo.

Cada torneo es diferente debido a tres fuentes principales de aleatoriedad:

- Lesiones de jugadores
- Resultados de partidos
- Variabilidad de goles (modelo probabilístico)

El resultado final es una distribución de probabilidades de clasificación para cada selección.

---

## 2. Datos de entrada

El modelo utiliza dos fuentes principales:

### `player_mundial.csv`

Contiene los jugadores de cada selección con:

- Puntuación individual
- Posición
- Probabilidad de lesión durante el torneo

### `fase_grupos.csv`

Define la composición de los grupos del torneo con 4 equipos por grupo.

### 2.1 Cálculo de los valores del modelo

Para cada jugador se realiza scraping de su perfil en **Transfermarkt**, del cual se obtiene:

- Posición
- Edad
- Historial de lesiones
- Valor de mercado

#### Probabilidad de lesión

La probabilidad de lesión se aproxima mediante un modelo probabilístico simple basado en un ratio histórico de lesiones del jugador.

En una versión idealizada del modelo, este riesgo podría modelarse con una distribución de Poisson, donde la tasa (λ) representa el número esperado de lesiones por unidad de tiempo:

$$\lambda = \frac{\text{número de lesiones}}{\text{tiempo de exposición}}$$

El tiempo de exposición se aproxima como:

$$\text{tiempo de exposición} = \text{edad} - 16$$

Se asume que a partir de los 16 años el jugador entra en entorno profesional y comienza la exposición relevante al riesgo de lesión.

> **Importante:** esto es una aproximación estadística simplificada, no un modelo médico real.

#### Puntuación del jugador

En este modelo, la puntuación de cada jugador se define directamente como su **valor de mercado**.

Se asume la hipótesis de que el valor de mercado está correlacionado con la calidad deportiva del jugador. Esta aproximación introduce sesgos, pero permite construir un proxy consistente y escalable de rendimiento.

---

## 3. Cálculo de fuerza de cada selección

En cada simulación del torneo:

### 3.1 Lesiones

Al inicio de cada simulación se determinan los jugadores lesionados.

- Cada jugador puede quedar fuera del torneo según su probabilidad individual de lesión.
- Las lesiones afectan **toda** la simulación del Mundial (no se recalculan partido a partido).

### 3.2 Once ideal

Cada selección construye su mejor alineación posible con sistema **1-4-3-3**:

| Posición | Jugadores |
|---|---|
| Portero | 1 |
| Defensas | 4 |
| Centrocampistas | 3 |
| Delanteros | 3 |

Se seleccionan los mejores jugadores disponibles (no lesionados) por posición según su puntuación.

### 3.3 Poder del equipo

El poder del equipo se calcula como la **suma de las puntuaciones de los titulares**.

Este valor representa la fuerza global de la selección en esa simulación concreta.

---

## 4. Simulación de partidos

### 4.1 Modelo de Poisson (goles)

En la versión más realista del simulador, los partidos no se deciden directamente, sino mediante simulación de goles.

Donde:
- `p_A` = Puntuación de la selección A
- `p_B` = Puntuación de la selección B

Cada equipo recibe una tasa esperada de goles (λ):

$$\lambda_A = base \times \frac{p_A^{1.3}}{p_A^{1.3} + p_B^{1.3}}$$
$$\lambda_B = base \times \frac{p_B^{1.3}}{p_A^{1.3} + p_B^{1.3}}$$

Donde `base` ≈ media de goles por equipo por partido.
El exponente `1.3` amplifica diferencias entre equipos fuertes y débiles.

Los goles se generan como:

$$\text{goles}_A \sim \text{Poisson}(\lambda_A)$$
$$\text{goles}_B \sim \text{Poisson}(\lambda_B)$$

La distribución de Poisson se usa porque modela procesos de conteo de eventos raros en un intervalo fijo (en este caso, goles en un partido).

#### El exponente 1.3: un hiperparámetro

El exponente `1.3` presente en la función pitagórica **no proviene de ninguna teoría matemática específica ni de la distribución de Poisson**. Es un hiperparámetro elegido manualmente cuya función es controlar cuánto se amplifican las diferencias de calidad entre selecciones.

**Sin exponente** (`exp = 1`), si un equipo dobla en poder al rival:

```
A = 100, B = 50
100 / (100 + 50) = 0.667  →  A recibe el 66.7% de los goles esperados
 50 / (100 + 50) = 0.333  →  B recibe el 33.3% de los goles esperados
```

**Con exponente 1.3**, las diferencias se amplifican:

```
100^1.3 ≈ 398
 50^1.3 ≈ 162

398 / (398 + 162) = 0.711  →  A recibe el 71.1% de los goles esperados
162 / (398 + 162) = 0.289  →  B recibe el 28.9% de los goles esperados
```

**¿Por qué precisamente 1.3?** La respuesta honesta es: porque es un valor razonable que produce resultados plausibles. Modelos como Elo, Pythagorean Expectation o Bradley-Terry incluyen parámetros similares ajustados empíricamente para que las probabilidades simuladas se aproximen a los resultados reales.

La forma correcta de obtener ese exponente sería **calibrarlo** sobre datos históricos:

1. Reunir miles de partidos internacionales históricos.
2. Calcular el poder de cada selección antes de cada partido.
3. Probar distintos exponentes y evaluar cuál minimiza el error de predicción.

Por ejemplo, usando **Log Loss**, **Brier Score** o **error cuadrático medio**:

```
exp = 1.0  →  error 0.223
exp = 1.1  →  error 0.217
exp = 1.2  →  error 0.211
exp = 1.3  →  error 0.208  ✓ mejor resultado
exp = 1.4  →  error 0.210
exp = 1.5  →  error 0.216
```

En ese caso, se elegiría `1.3` porque es el que mejor predice los partidos históricos.

En mi caso he optado por 1.3 por tema de recursos y tiempo dado que viendo algunos ejemplos ha sido una buena aproximación.

#### Determinación del resultado

| Condición | Resultado |
|---|---|
| `goles_A > goles_B` | Gana A |
| `goles_B > goles_A` | Gana B |
| Empate en fase de grupos | Empate válido |
| Empate en eliminatorias | Se resuelve por penaltis aleatorios |

---

## 5. Fase de grupos

Cada grupo se juega en formato **todos contra todos** (6 partidos por grupo).

#### Sistema de puntuación

| Resultado | Puntos |
|---|---|
| Victoria | 3 |
| Empate | 1 |
| Derrota | 0 |

#### Clasificación

Los equipos se ordenan por:

1. Puntos totales
2. Desempate H2H (head-to-head entre empatados)
3. Sorteo aleatorio si persiste el empate

#### Clasificación a eliminatorias

- 1º y 2º de cada grupo clasifican directamente
- Los 8 mejores terceros también clasifican según puntos

---

## 6. Fase eliminatoria

El modelo implementa un bracket estructurado basado en el formato del torneo.

> **Nota importante:** La asignación de terceros en dieciseisavos es una aproximación del sistema oficial, ya que el reglamento completo depende de combinaciones específicas de grupos.

Incluye:

- Dieciseisavos de final (32 equipos)
- Octavos
- Cuartos
- Semifinales
- Final

Cada partido se simula individualmente y el perdedor queda eliminado.

---

## 7. Simulación Monte Carlo

El proceso completo se repite múltiples veces (ej: **50.000 simulaciones**).

En cada iteración se registra en qué fase cae cada selección:

| Fase |
|---|
| Fase de grupos |
| Dieciseisavos |
| Octavos |
| Cuartos |
| Semifinales |
| Finalista |
| Campeón |

---

## 8. Resultados finales

Las probabilidades se calculan como:

$$P(\text{evento}) = \frac{\text{veces que ocurre}}{\text{número total de simulaciones}}$$

Se exporta un **CSV** con las probabilidades de cada selección en cada fase.

El modelo permite:

- Estimar la probabilidad de que cada selección alcance cada fase del torneo.
- Generar visualizaciones de distribución de resultados por equipo.
- Calcular probabilidades acumuladas de clasificación a cada ronda.

---

## 9. Conclusión

Según el modelo, las selecciones con mayor probabilidad de ser **eliminadas en fase de grupos** son:

> Irak · Curazao · Jordania · Panamá

Por otro lado, las selecciones con mayor probabilidad de **proclamarse campeonas** son:

> Francia · Inglaterra · Portugal · España

...con una ventaja significativa respecto al resto.
