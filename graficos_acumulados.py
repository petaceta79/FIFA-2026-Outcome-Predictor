import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generar_graficos_acumulados(archivo_csv):
    # Comprobar si el archivo existe
    if not os.path.exists(archivo_csv):
        print(f"Error: No se encontró el archivo '{archivo_csv}'.")
        return

    # Leer los datos
    print("Cargando datos para generar los gráficos acumulados...")
    df = pd.read_csv(archivo_csv)

    # 🌟 CÁLCULO DE PROBABILIDAD ACUMULADA
    # Sumamos hacia adelante para saber si "llega" a esa ronda
    df['Llega_Dieciseisavos'] = df['Dieciseisavos_%'] + df['Octavos_%'] + df['Cuartos_%'] + df['Semis_%'] + df['Finalista_%'] + df['Campeon_%']
    df['Llega_Octavos'] = df['Octavos_%'] + df['Cuartos_%'] + df['Semis_%'] + df['Finalista_%'] + df['Campeon_%']
    df['Llega_Cuartos'] = df['Cuartos_%'] + df['Semis_%'] + df['Finalista_%'] + df['Campeon_%']
    df['Llega_Semis'] = df['Semis_%'] + df['Finalista_%'] + df['Campeon_%']
    df['Llega_Final'] = df['Finalista_%'] + df['Campeon_%']
    # La columna 'Campeon_%' ya la tenemos del CSV directamente

    # Configurar el estilo visual
    sns.set_theme(style="whitegrid")
    
    # Crear carpeta para guardar las imágenes
    carpeta_salida = "graficos_acumulados"
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    # Definir las fases y sus títulos
    fases = [
        ('Llega_Dieciseisavos', 'Probabilidad de Superar los Grupos (Top 32)'),
        ('Llega_Octavos', 'Probabilidad de Llegar a Octavos'),
        ('Llega_Cuartos', 'Probabilidad de Llegar a Cuartos'),
        ('Llega_Semis', 'Probabilidad de Llegar a Semifinales'),
        ('Llega_Final', 'Probabilidad de Llegar a la Gran Final'),
        ('Campeon_%', 'Probabilidad de Ser Campeón del Mundo')
    ]

    for i, (columna, titulo) in enumerate(fases):
        # 1. Ordenar de mayor a menor. 
        df_fase = df[['Seleccion', columna]].sort_values(by=columna, ascending=False)

        # 2. Hacer la imagen muy alta para que quepan las 48 selecciones
        plt.figure(figsize=(14, 20)) 
        
        # 3. Dibujar las barras
        paleta = "magma" if columna == 'Campeon_%' else "viridis"
        ax = sns.barplot(
            x=columna, 
            y='Seleccion', 
            data=df_fase, 
            palette=paleta,
            hue='Seleccion',
            legend=False
        )

        # 4. Títulos y etiquetas
        plt.title(titulo, fontsize=22, fontweight='bold', pad=20)
        plt.xlabel('Probabilidad Acumulada (%)', fontsize=16)
        plt.ylabel('', fontsize=16)
        
        # Ajustamos un poco la fuente de los equipos para que se lea perfecto
        plt.yticks(fontsize=11)

        # 5. Añadir los porcentajes exactos al lado de cada barra
        for p in ax.patches:
            ancho = p.get_width()
            plt.text(
                ancho + 0.3,       # Separación ligera a la derecha de la barra
                p.get_y() + p.get_height() / 2, 
                f"{ancho:.1f}%",   
                va="center", 
                fontsize=10, 
                color='black'
            )

        # 6. Ajustar márgenes dinámicamente
        limite_max = df_fase[columna].max()
        # Si el máximo es muy pequeño (ej. 0% en todas), damos un mínimo visual
        limite_max = max(limite_max * 1.10, 5) 
        plt.xlim(0, limite_max) 
        
        plt.tight_layout()

        # 7. Guardar el gráfico
        nombre_archivo = f"{carpeta_salida}/0{i + 1}_{columna.replace('%', '')}.png"
        plt.savefig(nombre_archivo, dpi=300) 
        plt.close() 

        print(f"  -> Generado: {nombre_archivo}")

    print("\n¡Todos los gráficos (con las 48 selecciones completas) se han guardado en la carpeta 'graficos_acumulados'!")

if __name__ == '__main__':
    archivo_resultados = 'resultados_montecarlo.csv'
    generar_graficos_acumulados(archivo_resultados)