# ibge_socioeconomico_elvira-brandao

Análises socioeconômicas e financeiras baseadas em dados do **IBGE (Censo 2022)** para as regiões do **Colégio Elvira Brandão — Chácara Santo Antônio e Morumbi (Vila Suzana)**, com foco em **renda**, **população** e **perfil econômico local**.

---

## 📘 Sobre o projeto

Este repositório reúne estudos analíticos desenvolvidos a partir de dados públicos do **IBGE (Censo 2022)**, com o objetivo de compreender o **perfil socioeconômico e populacional** das regiões em torno das unidades do **Colégio Elvira Brandão**.

As análises exploram indicadores como **renda média**, **população total**, **níveis de desigualdade** e **características demográficas locais**, servindo como base para **estratégias de marketing, captação e retenção de alunos**.

Os notebooks incluem **visualizações interativas**, **correlações estatísticas** e **agrupamentos por similaridade socioeconômica**, permitindo identificar padrões que influenciam o comportamento e o potencial econômico das regiões estudadas.

---

## 🧩 Estrutura do Repositório

O repositório está organizado em notebooks e arquivos complementares que documentam todo o processo analítico — da coleta e limpeza de dados à geração de visualizações e insights.

| Tipo de Arquivo | Nome | Descrição |
|------------------|------|------------|
| 📓 Notebook | `analise_financeira_chacara.ipynb` | Contém as análises socioeconômicas e populacionais da região de **Chácara Santo Antônio**, incluindo distribuição de renda, densidade populacional e correlação entre variáveis. |
| 📓 Notebook | `analise_financeira_morumbi.ipynb` | Realiza as mesmas análises para a unidade **Morumbi (Vila Suzana)**, permitindo comparações diretas entre as duas regiões. |
| 🌎 Mapa Interativo | `mapa_interativo_chacara.html` | Visualização interativa da distribuição de renda e população no entorno da unidade Chácara. |
| 🌎 Mapa Interativo | `mapa_interativo_morumbi.html` | Visualização interativa da região do Morumbi, destacando contrastes socioeconômicos e padrões territoriais. |
| ⚙️ Scripts de Apoio | arquivos em `functions_base_corrections/` e `cod_testes/` | Scripts auxiliares responsáveis por **padronização dos dados**, **correção de coordenadas geográficas** e **preenchimento automático de endereços** via APIs. |

---

Estes arquivos trabalham em conjunto para:
- 🧼 **Limpar e estruturar** dados censitários do IBGE;  
- 📊 **Gerar estatísticas e indicadores** sobre renda e população;  
- 📈 **Explorar correlações** e segmentar regiões com o algoritmo **K-means**;  
- 🗺️ **Visualizar insights geográficos** de forma interativa, com mapas dinâmicos.  

---

## 📊 Fontes de dados

- [Censo IBGE 2022 — Dados Demográficos](https://censo2022.ibge.gov.br/)  
- [API IBGE — Indicadores Sociais e Econômicos](https://servicodados.ibge.gov.br/api/docs/)

---

## 🎯 Objetivo

Com base nas análises realizadas, busca-se **compreender melhor o perfil financeiro e populacional das regiões próximas às unidades escolares**, visando apoiar decisões estratégicas relacionadas à **captação de leads**, **precificação** e **expansão de mercado**.

---

📍 *Projeto desenvolvido com foco em dados abertos, transparência e apoio à tomada de decisão estratégica na educação.*

---

✍️ **Feito por [Breno Rodrigues Azevedo](https://github.com/brenoazvd)**  
📅 São Paulo — 2025  
💡 *Análise de Dados e Inteligência Educacional*

---

## O que mudou (Resumo das ações recentes)

- **Atualização de caminhos CSV:** Notebooks em `analise_1.0/` agora usam caminhos relativos para os CSVs que estão na pasta raiz `filling_Ceps/`. Exemplo: `pd.read_csv('../filling_Ceps/Elvira Brandão Morumbi - ...csv')`.
- **Restauração de notebooks:** Os notebooks `analise_financeira_morumbi.ipynb` e `analise_financeira_chacara.ipynb` foram recriados com estrutura JSON válida após sofrerem corrupção durante uma alteração de caminhos. Os novos arquivos contêm células mínimas de carregamento e exploração de dados para facilitar testes iniciais.
- **Backups criados:** Antes da recriação foram gerados backups com timestamp (ex.: `analise_financeira_morumbi_backup_20251124_150557.ipynb` e `analise_financeira_chacara_backup_20251124_150557.ipynb`). Esses arquivos preservam o conteúdo corrompido para inspeção manual, se necessário.
- **Scripts temporários limpos:** Scripts de correção temporários foram removidos da raiz do projeto após a restauração.

---

## Como abrir e testar os notebooks (rápido)

- **Pré-requisitos:** Python 3.10+ (o projeto foi testado em 3.13.5), e pacotes comuns como `pandas`, `numpy`, `matplotlib`, `seaborn`, `folium`. Para instalar dependências rapidamente, por exemplo:

```powershell
python -m pip install pandas numpy matplotlib seaborn folium
```

- **Abrir notebook:** No VS Code ou Jupyter, abra `analise_1.0/analise_financeira_morumbi.ipynb` ou `analise_1.0/analise_financeira_chacara.ipynb`.
- **Executar a primeira célula de carregamento:** Ela usa `csv_path = '../filling_Ceps/<arquivo.csv>'` — verifique que os arquivos CSV relevantes estão em `filling_Ceps/` na raiz do repositório.
- **Exemplo de verificação manual em Python:**

```python
import pandas as pd
df = pd.read_csv('../filling_Ceps/Elvira Brandão Morumbi - Euvira Brandão Dados ADS_coords_corrigidas_com_enderecos.csv')
print(len(df), df.columns.tolist())
```

---

## Backups & recuperação

- Backups dos notebooks corrompidos estão localizados em `analise_1.0/` com sufixo `_backup_YYYYMMDD_HHMMSS.ipynb`. Recomendação: conservar esses arquivos até confirmar que as versões recriadas contém todo o conteúdo necessário.

- Caso queira restaurar uma versão anterior completa, sugiro mover o backup para outro local e abrir no Jupyter Notebook para inspecionar manualmente.

---

## Observações e próximos passos sugeridos

- **Verificar execução:** Execute as primeiras células dos dois notebooks recriados para confirmar que `pd.read_csv('../filling_Ceps/...')` carrega os CSVs corretamente. Relate qualquer `FileNotFoundError` com o caminho exato mostrado.
- **Revisar conteúdo:** As versões recriadas são mínimas — se houver código perdido que precise ser retomado, abra os backups e copie trechos úteis manualmente.
- **Commitar alterações:** Depois de validar localmente, recomendo commitar as mudanças e adicionar os notebooks ao controle de versão (se desejar incluir os notebooks completos no repositório). Exemplo de commit:

```powershell
git add README.md analise_1.0/analise_financeira_*.ipynb
git commit -m "Atualiza README e restaura notebooks com caminhos relativos para filling_Ceps"
```

---

Se quiser, eu posso:
- Executar um teste rápido (rodar a célula de carregamento) em ambos os notebooks aqui e retornar o resultado; ou
- Extrair trechos dos backups para tentar reconstruir mais conteúdo automaticamente.

Escolha qual dessas ações prefere que eu faça a seguir.
