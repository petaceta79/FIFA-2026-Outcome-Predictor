import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generar_graficos_eliminacion(archivo_csv):
    # Comprobar si el archivo existe
    if not os.path.exists(archivo_csv):
        print(f"Error: No se encontró el archivo '{archivo_csv}'.")
        return

    # Leer los datos
    print("Cargando datos para generar los gráficos...")
    df = pd.read_csv(archivo_csv)

    # Configurar el estilo visual
    sns.set_theme(style="whitegrid")
    
    # Crear carpeta para guardar las imágenes
    carpeta_salida = "graficos_eliminacion_exacta"
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    # Definir las fases (columnas originales del CSV) y sus títulos
    fases = [
        ('Grupos_%', 'Eliminados en Fase de Grupos'),
        ('Dieciseisavos_%', 'Eliminados en Dieciseisavos'),
        ('Octavos_%', 'Eliminados en Octavos de Final'),
        ('Cuartos_%', 'Eliminados en Cuartos de Final'),
        ('Semis_%', 'Eliminados en Semifinales (3º o 4º puesto)'),
        ('Finalista_%', 'Subcampeón (Perder la Final)'),
        ('Campeon_%', 'Probabilidad de ser CAMPEÓN DEL MUNDO')
    ]

    for i, (columna, titulo) in enumerate(fases):
        # 1. Ordenar de mayor a menor.
        df_fase = df[['Seleccion', columna]].sort_values(by=columna, ascending=False)

        # 2. Hacer la imagen muy alta (20 pulgadas) para que quepan las 48 selecciones
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
        plt.xlabel('Probabilidad (%)', fontsize=16)
        plt.ylabel('', fontsize=16)
        
        # Tamaño de letra ajustado para que los 48 países se lean bien
        plt.yticks(fontsize=11)

        # 5. Añadir los porcentajes exactos al lado de cada barra
        for p in ax.patches:
            ancho = p.get_width()
            plt.text(
                ancho + 0.3,       # Separación ligera a la derecha
                p.get_y() + p.get_height() / 2, 
                f"{ancho:.1f}%",   
                va="center", 
                fontsize=10, 
                color='black'
            )

        # 6. Ajustar márgenes dinámicamente
        limite_max = df_fase[columna].max()
        limite_max = max(limite_max * 1.10, 5) 
        plt.xlim(0, limite_max) 
        
        plt.tight_layout()

        # 7. Guardar el gráfico
        nombre_archivo = f"{carpeta_salida}/0{i + 1}_{columna.replace('%', '')}.png"
        plt.savefig(nombre_archivo, dpi=300) 
        plt.close() 

        print(f"  -> Generado: {nombre_archivo}")

    print("\n¡Todos los gráficos (con las 48 selecciones) se han guardado en la carpeta 'graficos_eliminacion_exacta'!")

if __name__ == '__main__':
    archivo_resultados = 'resultados_montecarlo.csv'
    generar_graficos_eliminacion(archivo_resultados)