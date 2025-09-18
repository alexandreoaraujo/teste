# Comparador de Preços de Compras

Aplicativo de linha de comando para registrar e consultar os menores preços
encontrados para itens do dia a dia. O programa salva os dados em um arquivo
JSON (`shopping_data.json` por padrão) para que você possa consultar o melhor
preço normal e o melhor preço promocional de cada produto sempre que precisar.

## Requisitos

- Python 3.11 ou superior

Opcionalmente, crie um ambiente virtual e instale o `pytest` para executar os
testes automatizados.

```bash
python -m venv .venv
source .venv/bin/activate
pip install pytest
```

## Uso básico

Os exemplos abaixo assumem que você está na raiz do projeto.

```bash
# adiciona preços
python app.py add "Alho" 3,00 --unit kg --store "Mercado Central"
python app.py add "Alho" 2,50 --promo --unit kg --store "Feira" --notes "promoção relâmpago"

# consulta o melhor preço para um item
python app.py search alho

# lista todos os itens cadastrados
python app.py list

# exibe os preços registrados para um item específico
python app.py entries "Alho"

# atualiza um registro
python app.py update "Alho" 1 --price 2,80 --store "Mercado do Bairro"

# remove um registro
python app.py remove "Alho" 2

# renomeia um item
python app.py rename "Alho" "Alho Roxo"
```

Use o parâmetro `--storage` em qualquer comando para alterar o caminho do
arquivo de dados:

```bash
python app.py --storage meus_precos.json list
```

## Executando os testes

```bash
pytest
```
