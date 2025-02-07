import plotly.express as px
import pandas as pd
import plotly.io as pio
import time
import os


df = pd.read_csv("desempenho.csv")

tamanhos = df["tamanho"].unique()

tamanhos = list(tamanhos) + [tamanhos[0]]

figs = []
for tamanho in tamanhos:

    # Tem que criar isso para evitar um bug do Plotly
    dummy_file = "dummy.pdf"
    x = [10, 100, 1000, 10000]
    y = [100, 200, 300, 400]

    fig_dummy = px.scatter(x=x, y=y)
    fig_dummy.write_image(dummy_file, format='pdf')
    time.sleep(0.1)

    df_filtrado = df[df["tamanho"] == tamanho]
    fig = px.line(
        df_filtrado,
        x="conexoes",
        y="tempo",
        title=f"Análise de Desempenho - {tamanho}",
        markers=True,
        labels={"conexoes": "Número de Conexões",
                "tempo": "Tempo de Download (s)"}
    )
    fig.update_layout(
        font=dict(size=18)  # Aumentando o tamanho da fonte
    )
    fig.show()

    # Exportar como PDF
    pio.write_image(fig, f"analise_desempenho_{tamanho}.pdf")

os.remove(dummy_file)
