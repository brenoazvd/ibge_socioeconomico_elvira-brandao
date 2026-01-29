# ibge_socioeconomico_elvira-brandao

Análises socioeconômicas e financeiras baseadas em dados do **IBGE (Censo 2022)** para as regiões do **Colégio Elvira Brandão — Chácara Santo Antônio e Morumbi (Vila Suzana)**, com foco em **renda**, **população** e **perfil econômico local**.

---

## Sobre o projeto

Este repositório reúne estudos analíticos desenvolvidos a partir de dados públicos do **IBGE (Censo 2022)**, com o objetivo de compreender o **perfil socioeconômico e populacional** das regiões em torno das unidades do **Colégio Elvira Brandão**.

As análises exploram indicadores como **renda média**, **população total**, **níveis de desigualdade** e **características demográficas locais**, servindo como base para **estratégias de marketing, captação e retenção de alunos**.

Os notebooks incluem **visualizações interativas**, **correlações estatísticas** e **agrupamentos por similaridade socioeconômica**, permitindo identificar padrões que influenciam o comportamento e o potencial econômico das regiões estudadas.

---

## Estrutura do repositório

O repositório está organizado em notebooks e arquivos complementares que documentam todo o processo analítico — da coleta e limpeza de dados à geração de visualizações e insights.

| Tipo | Arquivo | Descrição |
| --- | --- | --- |
| Notebook (Análise 1.0) | `analises/analise_1.0/morumbi_analise_financeira.ipynb` | Análises socioeconômicas da região Morumbi (Vila Suzana). |
| Notebook (Análise 1.0) | `analises/analise_1.0/chacara_analise_financeira.ipynb` | Análises socioeconômicas da região Chácara Santo Antônio. |
| Mapa interativo | `analises/analise_1.0/morumbi_mapa_interativo.html` | Mapa da renda e população no entorno do Morumbi. |
| Mapa interativo | `analises/analise_1.0/chacara_mapa_interativo.html` | Mapa da renda e população no entorno da Chácara. |
| Notebook (Análise 2.0) | `analises/analise_2.0/morumbi_analise_financeira_part2.ipynb` | Score de tráfego por CEP (Morumbi). |
| Notebook (Análise 2.0) | `analises/analise_2.0/chacara_analise_financeira_part2.ipynb` | Score de tráfego por CEP (Chácara). |
| Ranking por CEP | `analises/analise_2.0/morumbi_top_ceps_2026.csv` | CEPs ranqueados por score (Morumbi). |
| Ranking por CEP | `analises/analise_2.0/chacara_top_ceps_2026.csv` | CEPs ranqueados por score (Chácara). |
| Análise 3.0 (bairros) | `analises/analise_3.0/morumbi_score_bairros_latlon_2026.csv` | Score por bairro usando lat/lon. |
| Análise 3.0 (bairros) | `analises/analise_3.0/morumbi_bairros_proximos_relatorio.md` | Relatório de bairros próximos e priorização para vídeos. |
| Relatório HTML (Análise 3.0) | `analises/analise_3.0/morumbi_bairros_proximos_relatorio.html` | Visualização local no navegador. |
| Script | `analises/analise_3.0/analise_bairros_chacara_morumbi.py` | Gera a análise 3.0 usando lat/lon. |
| Scripts de apoio | `scripts/` | Padronização de dados, correções e scripts auxiliares. |
| Bases de entrada | `data/filling_Ceps/` | CSVs com lat/lon e endereços preenchidos. |

---

## Análises (resumo rápido)

- **Análise 1.0**: visão socioeconômica com mapas interativos por renda e população.
- **Análise 2.0**: score de tráfego por **CEP** com renda corrigida e crianças 0–9 anos.
- **Análise 3.0**: score por **bairro** usando lat/lon + distância até a escola.

---

## Pipeline (processo completo)

1) **Base bruta**  
   - `data/base_bruta.csv`

2) **Correção de lat/lon**  
   - Script: `scripts/corrigir_latlon.py`  
   - Saída: `data/base_coords_corrigidas.csv`

3) **Enriquecimento de endereços e CEPs**  
   - Script: `scripts/atualizar_enderecos_openaddresses.py`  
   - Saída: `data/base_principal.csv` (base oficial usada nas análises)

4) **Análise 1.0 (mapas e clusters)**  
   - Notebooks:  
     - `analises/analise_1.0/morumbi_analise_financeira.ipynb`  
     - `analises/analise_1.0/chacara_analise_financeira.ipynb`  
   - Saídas: mapas HTML e `*_clusters.csv`

5) **Análise 2.0 (CEPs e score)**  
   - Notebooks:  
     - `analises/analise_2.0/morumbi_analise_financeira_part2.ipynb`  
     - `analises/analise_2.0/chacara_analise_financeira_part2.ipynb`  
   - Relatórios HTML:  
     - `analises/analise_2.0/ceps_relatorio_morumbi_2026.html`  
     - `analises/analise_2.0/ceps_relatorio_chacara_2026.html`

6) **Análise 3.0 (bairros e score)**  
   - Script: `analises/analise_3.0/analise_bairros_chacara_morumbi.py`  
   - Saídas:  
     - `analises/analise_3.0/*_score_bairros_latlon_2026.csv`  
     - `analises/analise_3.0/*_bairros_proximos_relatorio.{md,html}`

---

## Fontes de dados

- [Censo IBGE 2022 — Dados Demográficos](https://censo2022.ibge.gov.br/)
- [API IBGE — Indicadores Sociais e Econômicos](https://servicodados.ibge.gov.br/api/docs/)

---

## Objetivo

Com base nas análises realizadas, busca-se **compreender melhor o perfil financeiro e populacional das regiões próximas às unidades escolares**, visando apoiar decisões estratégicas relacionadas à **captação de leads**, **precificação** e **expansão de mercado**.

---

*Projeto desenvolvido com foco em dados abertos, transparência e apoio à tomada de decisão estratégica na educação.*

Feito por [Breno Rodrigues Azevedo](https://github.com/brenoazvd) — São Paulo, 2026

---

## O que mudou (Resumo das ações recentes)

- **Padronização de nomes**: arquivos renomeados com prefixos `morumbi_` e `chacara_`.
- **Separação da análise de bairros**: novos outputs em `analises/analise_3.0/`.
- **Limpeza de utilitários não usados**: scripts de PySpark removidos.
- **Mapa do repositório**: guia rápido em `docs/MAPA_DO_REPO.md`.

---

## Como abrir e testar os notebooks (rápido)

- **Pré-requisitos:** Python 3.10+ e pacotes como `pandas`, `numpy`, `matplotlib`, `seaborn`, `folium`.

```powershell
python -m pip install pandas numpy matplotlib seaborn folium
```

- **Análise 1.0:** abra `analises/analise_1.0/morumbi_analise_financeira.ipynb` ou `analises/analise_1.0/chacara_analise_financeira.ipynb`.
- **Análise 2.0:** abra `analises/analise_2.0/morumbi_analise_financeira_part2.ipynb` ou `analises/analise_2.0/chacara_analise_financeira_part2.ipynb`.
- **Análise 3.0 (bairros):** execute o script abaixo para regenerar CSV e relatório:

```powershell
python analises/analise_3.0/analise_bairros_chacara_morumbi.py --output-dir analises/analise_3.0
```

Parâmetros úteis:
- `--min-pontos`: mínimo de pontos por bairro no ranking.
- `--top-n`: tamanho das listas de proximidade e score.
- `--top-videos`: quantidade de bairros sugeridos para vídeos.
- `--escola-lat` e `--escola-lon`: coordenadas da unidade.

---

## Backups & recuperação

- Backups dos notebooks corrompidos estão localizados em `analises/analise_1.0/` com sufixo `_backup_YYYYMMDD_HHMMSS.ipynb`.
- Caso queira restaurar uma versão anterior completa, mova o backup para outro local e abra no Jupyter Notebook para inspecionar manualmente.

---

## Observações e próximos passos sugeridos

- **Mapa do repositório:** consulte `docs/MAPA_DO_REPO.md` para um guia rápido da estrutura atual.
- **Verificar execução:** execute as primeiras células dos notebooks para confirmar que `pd.read_csv('../../data/filling_Ceps/...')` carrega os CSVs corretamente.
- **Revisar conteúdo:** se houver código perdido, abra os backups e copie trechos úteis manualmente.

Se quiser, eu posso:
- Executar um teste rápido (rodar a célula de carregamento) em ambos os notebooks e retornar o resultado; ou
- Extrair trechos dos backups para tentar reconstruir mais conteúdo automaticamente.
