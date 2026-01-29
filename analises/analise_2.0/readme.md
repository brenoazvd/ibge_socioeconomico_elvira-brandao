# Analise 2.0 — CEPs (Morumbi e Chácara)

Pipeline oficial da **Analise 2.0**, utilizando o **motor da Analise 3.0** (OSRM em lote + cache persistente), com agregação por **CEP** e geração automática de **CSV + HTML**.

---

## ▶️ Como executar (comando único)

Da raiz do projeto:

```bash
python analises/analise_2.0/analise_ceps_chacara_morumbi.py
```

Esse comando:
- processa **Morumbi** e **Chácara** no mesmo run
- calcula distâncias reais por carro (OSRM)
- cria cache fixo por CEP
- gera todos os CSVs finais
- gera automaticamente os relatórios HTML

---

## 📦 Base de dados

Fonte única oficial:

- `data/base_principal.csv`
  - já contém:
    - CEP corrigido
    - bairro corrigido
    - latitude / longitude do centro do setor
    - população total
    - renda média
    - variáveis etárias

---

## 🧭 Distância até a escola

- Método: **OSRM /table (em lote)**
- Distância real por carro, em km
- Ponto usado: **centroide do CEP** (mediana lat/lon)

### Cache permanente

As distâncias são salvas em:

```
data/cache/cep_distancias_cache.csv
```

Comportamento:
- primeira execução → calcula tudo (mais lenta)
- execuções seguintes → lê do cache (segundos)

---

## 👶 Faixas etárias utilizadas

### Morumbi
- `0–4`
- `5–9`
- `0–9`

### Chácara
- `0–4`
- `5–9`
- `10–14`
- `15–19`
- `0–19`

Cada CSV contém **apenas a faixa etária correspondente**.

---

## 📊 Agregação por CEP

Para cada CEP:

- `renda_mediana_2026` → mediana da renda (com inflação aplicada)
- `Populacao` → mediana da população
- `criancas_x_y` → mediana da faixa etária solicitada
- `distancia_mediana_km` → distância até a escola
- `pontos` → quantidade de registros no CEP

CEP é sempre salvo no formato padrão:

```
#####-###
```

---

## 🧮 Scores

### Score de Tráfego

```python
score_trafego_2026 = renda_mediana_2026 * criancas
```

Representa potencial bruto de demanda.

---

### Score Composto (principal ranking)

Componentes normalizados por rank percentual:

- renda
- crianças
- proximidade (1 – rank da distância)

Fórmula final:

```python
score_composto_2026 = (
    0.5 * proximidade_rank
  + 0.25 * renda_rank
  + 0.25 * criancas_rank
) * 100
```

Interpretação:
- proximidade pesa mais (50%)
- renda e crianças equilibram (25% cada)

---

## 📁 Arquivos gerados

Todos os arquivos são salvos em:

```
analises/analise_2.0/out/
```

### Morumbi

- `morumbi_ceps_idade_0_4_2026.csv`
- `morumbi_ceps_idade_5_9_2026.csv`
- `morumbi_ceps_idade_0_9_2026.csv`

---

### Chácara

- `chacara_ceps_idade_0_4_2026.csv`
- `chacara_ceps_idade_5_9_2026.csv`
- `chacara_ceps_idade_10_14_2026.csv`
- `chacara_ceps_idade_15_19_2026.csv`
- `chacara_ceps_idade_0_19_2026.csv`

---

## 🖼️ Relatórios HTML

Gerados automaticamente ao final do pipeline:

- `ceps_relatorio_morumbi_2026.html`
- `ceps_relatorio_chacara_2026.html`

Conteúdo:
- ranking completo por distância
- renda, crianças, população
- score de tráfego
- score composto

---

## ⚙️ Observações importantes

- Não usar notebooks antigos para produção
- Este script é a **versão oficial da Analise 2.0**
- Scripts e notebooks antigos são considerados **legado**

---

## 🏁 Status do pipeline

| Item | Status |
|------|--------|
| Base única | ✅ |
| Agregação por CEP | ✅ |
| Distância real OSRM | ✅ |
| Cache persistente | ✅ |
| Duas unidades no mesmo run | ✅ |
| CSV limpo por faixa | ✅ |
| HTML automático | ✅ |
| Performance estável | ✅ |

---

**Analise 2.0 encerrada e estabilizada.**  
Motor idêntico à Analise 3.0.  
Pronta para uso estratégico e tomada de decisão. 🚀
