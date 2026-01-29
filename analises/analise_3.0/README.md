# Analise 3.0 - Bairros (lat/lon)

Esta pasta concentra a analise de bairros usando lat/lon e distancia ate a
escola. Ela gera score por bairro e relatorios HTML no mesmo layout da
Analise 2.0.

Os scripts preferem a base em `data/base_principal.csv`, com
fallback automatico para `data/filling_Ceps/` se necessario.

Arquivos principais (script classico):
- `morumbi_score_bairros_latlon_2026.csv`
- `morumbi_bairros_proximos_relatorio.md`
- `morumbi_bairros_proximos_relatorio.html`

Arquivos principais (script novo, estilo Analise 2.0):
- `analises/analise_3.0/out/chacara_bairros_relatorio_2026.html`
- `analises/analise_3.0/out/morumbi_bairros_relatorio_2026.html`
- CSVs por faixa em `analises/analise_3.0/out/`:
  - `*_bairros_idade_0_19_2026.csv` (Chacara, ordenado por distancia)
  - `*_bairros_idade_0_4_2026.csv`
  - `*_bairros_idade_5_9_2026.csv`
  - `*_bairros_idade_10_14_2026.csv` (Chacara)
  - `*_bairros_idade_15_19_2026.csv` (Chacara)
  - `*_bairros_idade_0_9_2026.csv` (Morumbi)

Para regenerar os arquivos (script classico; se nao passar `--unidade`, roda Morumbi e Chacara automaticamente):
```
python analises/analise_3.0/analise_bairros_chacara_morumbi.py --output-dir analises/analise_3.0
```
Para a Chacara, use `--unidade chacara` e ajuste `--escola-lat/--escola-lon`.

Para regenerar os arquivos no layout da Analise 2.0 (CSV + HTML):
```
python analises/analise_3.0/analise_bairros_chacara_morumbi_bairros_v4.py
```

Para visualizar, abra:
- `analises/analise_3.0/out/chacara_bairros_relatorio_2026.html`
- `analises/analise_3.0/out/morumbi_bairros_relatorio_2026.html`

Opcional: ha copias dos HTMLs tambem em `analises/analise_3.0/`.

Parametros uteis (script classico):
- `--min-pontos`: minimo de pontos por bairro no ranking.
- `--top-n`: tamanho das listas de proximidade e score.
- `--top-videos`: quantidade de bairros sugeridos para videos.
- `--escola-lat` e `--escola-lon`: coordenadas da unidade.
- `--distance-mode`: `osrm` (carro, padrao) ou `haversine` (linha reta).
- Distancia por bairro: rota calculada a partir da mediana das lat/lon dos CEPs do bairro. Se o OSRM falhar, a distancia fica vazia.

## CEP/logradouro e bairro (OpenAddresses + ViaCEP)

Atualiza CEP/logradouro via OpenAddresses e bairro/cidade/UF via ViaCEP:
```
python scripts/atualizar_enderecos_openaddresses.py --download --overwrite --via-cep
```

Opcoes uteis:
- `--via-cep-logradouro`: sobrescreve logradouro com ViaCEP (opcional).
- `--backup-bairro`: salva o bairro atual em `Bairro_original` antes da troca.
- `--clear-unused-bairro-cols`: limpa `Bairro_osm/Bairro_geosampa` para evitar confusao.

Requer `scipy` instalado:
```
python -m pip install scipy
```
