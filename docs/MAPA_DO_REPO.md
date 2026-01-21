# Mapa do repositorio

Objetivo: facilitar onde estao as analises, dados e scripts ativos.

## Pastas principais
- `analises/`: analises 1.0, 2.0 e 3.0 (notebooks, mapas, relatorios).
- `data/`: bases oficiais (bruta, coords corrigidas, principal) e espelho `data/filling_Ceps/`.
- `scripts/`: scripts ativos de atualizacao e analise.
- `docs/`: documentacao do projeto.

## Arquivos chave
- `data/base_bruta.csv`
- `data/base_coords_corrigidas.csv`
- `data/base_principal.csv`
- `analises/analise_1.0/morumbi_analise_financeira.ipynb`
- `analises/analise_1.0/chacara_analise_financeira.ipynb`
- `analises/analise_2.0/morumbi_analise_financeira_part2.ipynb`
- `analises/analise_2.0/chacara_analise_financeira_part2.ipynb`
- `analises/analise_3.0/morumbi_score_bairros_latlon_2025.csv`
- `analises/analise_3.0/morumbi_bairros_proximos_relatorio.md`
- `analises/analise_3.0/morumbi_bairros_proximos_relatorio.html`
- `analises/analise_3.0/README.md`
- `scripts/_datasets.py`
- `scripts/analise_bairros_morumbi_latlon.py`
- `scripts/atualizar_enderecos_openaddresses.py`

## Rodar analise de bairros (lat/lon)
```
python scripts/analise_bairros_morumbi_latlon.py --output-dir analises/analise_3.0
```

Parametros uteis:
- `--escola-lat` / `--escola-lon`: coordenadas da unidade.
- `--min-pontos`: minimo de pontos por bairro para o ranking.
- `--top-n`: tamanho do ranking de bairros (proximos e top score).
- `--top-videos`: quantidade de bairros sugeridos para videos.

## Atualizar CEP/logradouro e bairro (OpenAddresses + ViaCEP)
```
python scripts/atualizar_enderecos_openaddresses.py --download --overwrite --via-cep
```
