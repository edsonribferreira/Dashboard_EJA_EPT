# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. CONFIGURAÇÕES INICIAIS
# ==========================================
st.set_page_config(page_title="Painel EJA-EPT - IFF", layout="wide")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1L_78f9AnCi2a5se7nwc0Qe4RVmNjb5Aznykb74lF3A0/edit?usp=sharing"

# Estabelece a conexão com os "Secrets" do Streamlit
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 2. FUNÇÕES DE DADOS (NUVEM)
# ==========================================
def ler_dados_nuvem():
    try:
        # ttl=0 obriga o Streamlit a buscar o dado real agora, ignorando a memória
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Página1", ttl=0)
        return df.dropna(how='all') 
    except:
        return pd.DataFrame()

def salvar_dados_nuvem(df_novo):
    df_atual = ler_dados_nuvem()
    
    if not df_atual.empty:
        df_consolidado = pd.concat([df_atual, df_novo], ignore_index=True)
    else:
        df_consolidado = df_novo
        
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Página1", data=df_consolidado)
    st.cache_data.clear() # Limpa o cache imediatamente após salvar

def apagar_dados_nuvem():
    # Substitui a planilha por um DataFrame vazio para resetar
    conn.update(spreadsheet=URL_PLANILHA, worksheet="Página1", data=pd.DataFrame())
    st.cache_data.clear()

# ==========================================
# 3. INTERFACE PRINCIPAL
# ==========================================
st.title("Painel de Dados - Programa EJAEPT - IFF")

# --- ÁREA DE UPLOAD E MAPEAMENTO ---
with st.expander("⬆️ Alimentar Base de Dados"):
    novo_arquivo = st.file_uploader("Suba o CSV com os dados", type=['csv'])
    
    if novo_arquivo:
        df_temp = pd.read_csv(novo_arquivo)
        colunas_csv = list(df_temp.columns)
        
        st.write("### Mapeamento de Colunas")
        st.info("Verifique se o sistema conectou as colunas do seu arquivo corretamente:")
        
        colunas_obrigatorias = ['nome_estudante', 'curso', 'campus', 'municipio', 'bairro', 'etnia', 'renda', 'sexo']
        
        def adivinhar_coluna(padrao, col_disponiveis):
            dicas = {
                'nome_estudante': ['nome', 'aluno', 'completo'], 'curso': ['curso'], 'campus': ['campus', 'polo'],
                'municipio': ['município', 'cidade'], 'bairro': ['bairro'], 'etnia': ['etnia', 'cor', 'raça'],
                'renda': ['renda'], 'sexo': ['sexo', 'gênero']
            }
            for col in col_disponiveis:
                if any(dica in col.lower() for dica in dicas.get(padrao, [])):
                    return col
            return "❌ Não existe no arquivo"

        mapa_colunas = {}
        valores_padrao = {}
        
        for col_padrao in colunas_obrigatorias:
            opcoes = ["❌ Não existe no arquivo"] + colunas_csv
            palpite = adivinhar_coluna(col_padrao, colunas_csv)
            
            c1, c2 = st.columns([1, 1])
            with c1:
                escolha = st.selectbox(f"Coluna para **{col_padrao.upper()}**:", options=opcoes, index=opcoes.index(palpite))
                mapa_colunas[col_padrao] = escolha
            
            with c2:
                if escolha == "❌ Não existe no arquivo":
                    valores_padrao[col_padrao] = st.text_input(f"Digite o valor para todas as linhas:", key=f"txt_{col_padrao}", placeholder="Ex: Libras")
                else:
                    st.write("") 
                    
        if st.button("Confirmar Mapeamento e Salvar na Nuvem"):
            df_final = pd.DataFrame()
            
            for col_padrao in colunas_obrigatorias:
                escolha = mapa_colunas[col_padrao]
                if escolha == "❌ Não existe no arquivo":
                    df_final[col_padrao] = valores_padrao.get(col_padrao, "Não Informado")
                else:
                    df_final[col_padrao] = df_temp[escolha]
                    
            salvar_dados_nuvem(df_final)
            st.success("✅ Dados padronizados e salvos permanentemente no Google Sheets!")


# ==========================================
# 4. DASHBOARD / GRÁFICOS
# ==========================================
df = ler_dados_nuvem()

if not df.empty:
    colunas_analise = [col for col in df.columns if col not in ['nome_estudante']]

    st.sidebar.header("Filtros Globais")
    st.sidebar.write("Filtre a base antes de gerar o gráfico:")
    df_filtrado = df.copy()

    for col in colunas_analise:
        valores_unicos = df[col].dropna().unique()
        selecao = st.sidebar.multiselect(f"{col.capitalize()}", options=valores_unicos, default=[])
        if selecao:
            df_filtrado = df_filtrado[df_filtrado[col].isin(selecao)]

    st.header("Construtor de Gráficos")

    c1, c2, c3 = st.columns(3)
    with c1:
        eixo_x = st.selectbox("1. Escolha a Categoria Principal (Eixo X):", colunas_analise)
    with c2:
        divisao_cor = st.selectbox("2. Cruzar com (Subdivisão/Cor):", ['Nenhum'] + colunas_analise)
    with c3:
        tipo_grafico = st.selectbox("3. Tipo de Gráfico:", ["Barras Agrupadas", "Barras Empilhadas", "Dispersão", "Pizza / Donut"])

    st.divider()

    if len(df_filtrado) == 0:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        st.write(f"**Analisando {len(df_filtrado)} registros filtrados.**")

        if divisao_cor != 'Nenhum':
            df_agrupado = df_filtrado.groupby([eixo_x, divisao_cor]).size().reset_index(name='Quantidade')

            if tipo_grafico == "Barras Agrupadas":
                fig = px.bar(df_agrupado, x=eixo_x, y='Quantidade', color=divisao_cor, barmode='group')
            elif tipo_grafico == "Barras Empilhadas":
                fig = px.bar(df_agrupado, x=eixo_x, y='Quantidade', color=divisao_cor)
            elif tipo_grafico == "Dispersão":
                fig = px.scatter(df_agrupado, x=eixo_x, y='Quantidade', color=divisao_cor, size='Quantidade')
            else: 
                fig = px.sunburst(df_agrupado, path=[eixo_x, divisao_cor], values='Quantidade')
        else:
            df_agrupado = df_filtrado[eixo_x].value_counts().reset_index()
            df_agrupado.columns = [eixo_x, 'Quantidade']

            if tipo_grafico in ["Barras Agrupadas", "Barras Empilhadas"]:
                fig = px.bar(df_agrupado, x=eixo_x, y='Quantidade', color=eixo_x)
            else:
                fig = px.pie(df_agrupado, names=eixo_x, values='Quantidade', hole=0.4)

        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ver Tabela de Dados Filtrados"):
        st.dataframe(df_filtrado)

else:
    st.info("Nenhum dado no sistema. Faça o upload do primeiro arquivo CSV.")

# ==========================================
# 5. RODAPÉ
# ==========================================
rodape_html = """
    <div style="text-align: center; color: #888888; font-size: 12px; margin-top: 30px; padding-bottom: 20px;">
        <p style="margin: 0; line-height: 1.4;">
            <b>💻Desenvolvido por Edson Ferreira - 2026</b><br>           
             Estudante de Análise e Desenvolvimento de Sistemas - PUCPR<br>
            📧 edsonferreira.dev@gmail.com
        </p>
    </div>
    """
st.markdown(rodape_html, unsafe_allow_html=True)
