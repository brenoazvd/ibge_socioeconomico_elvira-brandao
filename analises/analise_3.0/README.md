# Analise 3.0 - Bairros (lat/lon)

Esta pasta concentra a analise de bairros usando lat/lon e distancia ate a
unidade Morumbi. Ela gera um score de trafego por bairro e um relatorio de
priorizacao para videos.

Os scripts preferem a base em `data/base_principal.csv`, com
fallback automatico para `data/filling_Ceps/` se necessario.

Arquivos principais:
- `morumbi_score_bairros_latlon_2025.csv`
- `morumbi_bairros_proximos_relatorio.md`
- `morumbi_bairros_proximos_relatorio.html`

Para regenerar os arquivos:
```
python scripts/analise_bairros_morumbi_latlon.py --output-dir analises/analise_3.0
```
Para a Chacara, use `--unidade chacara` e ajuste `--escola-lat/--escola-lon`.

Para visualizar, abra `morumbi_bairros_proximos_relatorio.html` no navegador.

Parametros uteis:
- `--min-pontos`: minimo de pontos por bairro no ranking.
- `--top-n`: tamanho das listas de proximidade e score.
- `--top-videos`: quantidade de bairros sugeridos para videos.
- `--escola-lat` e `--escola-lon`: coordenadas da unidade.

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
