import pandas as pd

# Carregar o CSV com os dados
df = pd.read_csv('Elvira Brandão Morumbi - Euvira Brandão Dados ADS_coords_corrigidas_com_enderecos.csv')

# Verificando as primeiras linhas para ver o formato de 'renda_media'
print(df['renda_media'].head())

# Corrigir a coluna 'renda_media': remover 'R$', substituir ponto por vírgula como separador de milhar
df['renda_media'] = df['renda_media'].astype(str)  # Garantir que a coluna seja string
df['renda_media'] = df['renda_media'].str.replace('R\$', '', regex=True)  # Remove 'R$'

# Substitui ponto por vírgula para separar milhar e vírgula para decimal
df['renda_media'] = df['renda_media'].str.replace(r'(\d)(?=(\d{3})+(\,))', r'\1.', regex=True)  # Adiciona ponto como separador de milhar
df['renda_media'] = df['renda_media'].str.replace(',', '.', regex=False)  # Substitui vírgula por ponto na parte decimal

# Agora substitui ponto de volta para vírgula para ser usado no formato correto de 'milhares,centavos'
df['renda_media'] = df['renda_media'].str.replace('.', ',', regex=False)

# Verificar se a conversão foi bem-sucedida
print(df['renda_media'].head())

# Salvar o arquivo corrigido
df.to_csv('Elvira_Brandao_Morumbi_Corrigido_Fim.csv', index=False)

print('Arquivo corrigido salvo como "Elvira_Brandao_Morumbi_Corrigido_Fim.csv"')
